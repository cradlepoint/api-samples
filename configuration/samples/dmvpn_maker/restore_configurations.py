# Patches an "Undo" configuration that removes all settings that were patched by config_pusher.py

import json
import csv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from headers import ncm_headers

# Define headers
headers = ncm_headers.myheader

# Load ctrl-z payload
with open("./configs/config_backups/undo_changes.json", "r") as j:
    undo_payload = json.loads(j.read())


def restore_configs():
    """Pushes a config to remove all the additions from config_pusher.py"""

    # open CSV to read router ID's
    with open("test_routers.csv", "r") as f:
        config_csv = csv.reader(f)

        # open session to ncm
        with requests.Session() as s:
            # Set max retries to 3
            retries = Retry(
                total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]
            )

            s.mount("https://", HTTPAdapter(max_retries=retries))

            # Iterate through csv and patch config to routers
            for row, column in enumerate(config_csv):

                # skip header row
                if row == 0:
                    continue

                # exit when out of router ids
                if column[0] == "":
                    print("End of router id's reached, exiting program")
                    break  # No router id, exit program

                # get router id
                router_id = int(column[0])

                # initialize configuration_managers id
                cfg_id = ""

                try:
                    # Use this payload as the payload for this router
                    payload = undo_payload

                    # get configuration_managers id
                    cfg_id = s.get(
                        "https://www.cradlepointecm.com/api/v2/configuration_managers/?router.id={}".format(
                            router_id
                        ),
                        headers=headers,
                    ).json()
                    cfg_id = cfg_id.get("data")[0].get("id")

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

                # catch index errors, probably from a failed GET
                except IndexError as e:
                    print(
                        "{} IndexError, probably from failed GET. Exception = {}\nGET Response = {}\n".format(
                            router_id, e, cfg_id
                        )
                    )

                # catch very broad exceptions
                except Exception as e:
                    print("Error patching to {}\nException = {}\n".format(router_id, e))


if __name__ == "__main__":
    restore_configs()
