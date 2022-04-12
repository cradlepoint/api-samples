import argparse
import json
import logging
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime

headers = {
    "Content-Type": "application/json",
    "X-CP-API-ID": os.environ.get("X_CP_API_ID"),
    "X-CP-API-KEY": os.environ.get("X_CP_API_KEY"),
    "X-ECM-API-ID": os.environ.get("X_ECM_API_ID"),
    "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY"),
}


class NcmAPIv2(object):
    def __init__(self):
        self.resp_data = {"data": []}

    @staticmethod
    def establish_session():
        with requests.Session() as session:
            retries = Retry(
                total=5,  # Total number of retries to allow.
                backoff_factor=2,
                status_forcelist=[
                    408,  # 408 Request Timeout
                    500,  # 500 Internal Server Error
                    502,  # 502 Bad Gateway
                    503,  # 503 Service Unavailable
                    504,  # 504 Gateway Timeout
                ],
            )
            a = HTTPAdapter(max_retries=retries)
            session.mount("https://", a)

        return session

    def next_url(self):

        for item in self.resp["data"]:
            self.resp_data["data"].append(item)

        if args.page and self.resp["meta"]["next"]:
            self.url = self.resp["meta"]["next"]
            return self.url

        if args.steps and self.resp["meta"]["next"]:
            while args.steps != 0:
                args.steps -= 1
                self.url = self.resp["meta"]["next"]
                return self.url

    def get_data(self, get_url, json_output):

        session = self.establish_session()

        while get_url:

            logging.info(get_url)

            try:
                r = session.get(get_url, headers=headers, timeout=30, stream=True)

                if r.status_code != 200:
                    logging.info(str(r.status_code) + ": " + str(r.text))
                    break

                else:
                    self.resp = json.loads(r.content.decode("utf-8"))

                    if len(self.resp["data"]) < 1:
                        return self.resp

                    else:
                        get_url = self.next_url()

            except Exception as e:
                logging.info("Exception:", e)
                raise

        json_data = json.dumps(self.resp_data, indent=4, sort_keys=False)

        with open(f"json/{json_output}", "w") as outfile:
            outfile.write(json_data)

        return json_data


if __name__ == "__main__":

    # Create json and logs dir
    for path in ["json", "logs"]:
        dir_path = os.path.join(os.getcwd(), path)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError:
                raise

    # Setup logging information
    logging.basicConfig(
        filename=f'logs/{datetime.now().strftime("%d_%m_%Y_%H_%M_%S.log")}',
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse commandline options.
    parser = argparse.ArgumentParser(description="Query APIv2 Historical Locations")

    parser.add_argument("--ecm-api-id", help="Override X_ECM_API_ID")
    parser.add_argument("--ecm-api-key", help="Override X_ECM_API_KEY")
    parser.add_argument("--cp-api-id", help="Override X-CP-API-ID")
    parser.add_argument("--cp-api-key", help="Override X-CP-API-KEY")

    parser.add_argument("--endpoint", help="Name of API endpoint.", default="accounts")
    parser.add_argument("--account", help="Your NCM ID found in settings.")
    parser.add_argument(
        "--limit",
        help="Limit elements in reply, default is 500.",
        default=500,
    )
    parser.add_argument(
        "--page",
        help="Keep following the next URL.",
        action="store_true",
    )
    parser.add_argument(
        "--server",
        default="https://www.cradlepointecm.com",
        help="Base URL of server.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        help="Walk only this many steps.",
        default=-1,
    )
    parser.add_argument(
        "--output",
        help="json output file name and location",
        default="example.json",
    )

    args = parser.parse_args()

    if args.ecm_api_id:
        headers["X-ECM-API-ID"] = args.ecm_api_id
    if args.ecm_api_key:
        headers["X-ECM-API-KEY"] = args.ecm_api_key
    if args.cp_api_id:
        headers["X-CP-API-ID"] = args.cp_api_id
    if args.cp_api_key:
        headers["X-CP-API-KEY"] = args.cp_api_key

    url = f"{args.server}/api/v2/{args.endpoint}/"

    if args.limit:
        url += f"?limit={args.limit}"
    if args.account:
        url += f"&account={args.account}"

    output = args.output

    logging.info("Started")

    # Create an instance of the class
    s = NcmAPIv2()

    data = s.get_data(f"{url}", f"{output}")

    logging.info("Finished")
