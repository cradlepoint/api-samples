"""
The script works by iterating through a CSV file with Router IDs as the
first column.  It adds the unique settings needed for that router into
the json and then PATCHes the results to the router.  It then moves on
to the next Router ID until it reaches the bottom of the CSV.  It also
saves a backup of each routers configuration before making the PATCH.

By modifying the /configs/indi_config.json file and the CSV this can be
easily adapted to push any DMVPN configuration you want.

Made for Cradlepoint by Harvey Breaux
"""

import csv
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from headers import ncm_headers

# Define headers
headers = ncm_headers.myheaders

# create results csv and write headers
with open("results.csv", "a", newline="") as results:
    results_csv = csv.writer(results)
    results_csv.writerow(["Router ID", "Response", "Exceptions"])


def push_configs():
    """Pushes the config to each router ID"""

    # Load configuration json
    with open("./configs/indi_config.json", "r") as j:
        indi_payload = json.loads(j.read())

    # open config CSV. CSV column 0 should be the router IDs
    with open("test_routers.csv", "r") as f:
        config_csv = csv.reader(f)

        # Open session to ncm
        with requests.Session() as s:
            # Set max retries to 3
            retries = Retry(
                total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]
            )

            s.mount("https://", HTTPAdapter(max_retries=retries))

            # Iterate through csv and patch config to routers
            for row, column in enumerate(config_csv):
                payload = ""
                patch_result = ""
                patch_text = ""

                # skip header row
                if row == 0:
                    continue

                # exit when out of router ids
                if column[0] == "":
                    print("End of router id's reached, exiting program")
                    break

                # get values for ip, gre, etc
                router_id = int(column[0])
                gre_ip = column[1]
                gre_ip2 = column[5]  # This is an ip for a second gre tunnel
                gre_mask = column[2]
                local_network_ip = column[3]
                local_network_mask = column[4]

                # initialize configuration_managers id
                cfg_id = ""

                try:
                    # Fill in GRE info
                    indi_payload["configuration"][0]["gre"]["tunnels"][
                        "00000000-adbb-3f47-962c-cd7ea9a221af"
                    ]["local_network"] = gre_ip
                    indi_payload["configuration"][0]["gre"]["tunnels"][
                        "00000001-3248-3c72-96d3-adb4353e0501"
                    ]["local_network"] = gre_ip2

                    # Fill in LAN info
                    indi_payload["configuration"][0]["lan"][
                        "00000000-0d93-319d-8220-4a1fb0372b51"
                    ]["ip_address"] = local_network_ip
                    indi_payload["configuration"][0]["lan"][
                        "00000000-0d93-319d-8220-4a1fb0372b51"
                    ]["netmask"] = local_network_mask

                    # BGP config info
                    indi_payload["configuration"][0]["routing"]["bgp"]["routers"]["0"][
                        "router_id"
                    ] = local_network_ip
                    indi_payload["configuration"][0]["routing"]["bgp"]["routers"]["0"][
                        "networks"
                    ]["0"]["ip_network"] = (local_network_ip + "/27")

                    # Use this payload as the payload for this router
                    payload = indi_payload

                    # get configuration_managers id and save backup of config
                    cfg = s.get(
                        "https://www.cradlepointecm.com/api/v2/configuration_managers/?router.id={}".format(
                            router_id
                        ),
                        headers=headers,
                    )

                    # Check authorization
                    if cfg.status_code == 401:
                        raise requests.RequestException(
                            "401 Unauthorized response. Invalid Credentials i.e. missing or invalid keys."
                        )

                    # Get the configuration_managers id from the response
                    cfg_id = cfg.json().get("data")[0].get("id")

                    # save cfg backup
                    with open(
                        "./configs/config_backups/{}.json".format(router_id), "w"
                    ) as backup:
                        backup.write(str(cfg.json()))
                        print("backup created for {}".format(cfg_id))

                    # patch payload
                    patch = s.patch(
                        "https://www.cradlepointecm.com/api/v2/configuration_managers/{}/".format(
                            cfg_id
                        ),
                        headers=headers,
                        data=json.dumps(payload),
                    )

                    # print result
                    patch_result = patch.status_code
                    print(
                        "Config patch sent to router {}\nResponse = {}\n".format(
                            router_id, patch_result
                        )
                    )

                    # Catch failed status codes and log them
                    if patch_result is not 202:
                        print(
                            "Patch unsuccessful. Status code {}, Response: {}\n".format(
                                patch_result, patch.text
                            )
                        )
                        patch_text = patch.text

                # catch index errors, probably from a failed GET
                except IndexError as e:
                    print(
                        "{} IndexError, probably from failed GET. Exception = {}\nGET Response = {}\n".format(
                            router_id, e, cfg_id
                        )
                    )

                # catch broad exceptions
                except Exception as e:
                    print("Error patching to {}\nException = {}\n".format(router_id, e))

                # write patch result to csv
                finally:
                    with open("results.csv", "a", newline="") as patch_results:
                        patch_results_csv = csv.writer(patch_results)
                        patch_results_csv.writerow(
                            [router_id, patch_result, patch_text]
                        )


if __name__ == "__main__":
    push_configs()
