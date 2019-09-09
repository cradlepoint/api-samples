"""
NOTE: Cradlepoint does not develop, maintain, or support NCM API applications.
Applications are the sole responsibility of the developer.

WARNING: NCM API Applications can introduce security and other potential issues
when not carefully engineered. Test your code thoroughly before deploying it to
production devices. This can affect production devices and data!
"""

import argparse
import json
import os
import requests
import logging
import pprint
import sys
from os import environ
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime, timedelta

headers = {
    "Content-Type": "application/json",
    "X-CP-API-ID": environ.get("X_CP_API_ID"),
    "X-CP-API-KEY": environ.get("X_CP_API_KEY"),
    "X-ECM-API-ID": environ.get("X_ECM_API_ID"),
    "X-ECM-API-KEY": environ.get("X_ECM_API_KEY"),
}

endpoints = [
    'accounts',
    'activity_logs',
    'alerts',
    'configuration_managers',
    'device_app_bindings',
    'device_app_states',
    'device_app_versions',
    'device_apps',
    'firmwares',
    'groups',
    'locations',
    'net_device_health',
    'net_device_metrics',
    'net_device_signal_samples',
    'net_device_usage_samples',
    'net_devices',
    'products',
    'reboot_activity',
    'router_alerts',
    'router_logs',
    'router_state_samples',
    'router_stream_usage_samples',
    'routers',
    'speed_tests',
]


class NCM_APIv2(object):

    retry_total = 5

    retry_backoff = 2

    retry_list = [408,  # 408 Request Timeout
                  500,  # 500 Internal Server Error
                  502,  # 502 Bad Gateway
                  503,  # 503 Service Unavailable
                  504,  # 504 Gateway Timeout
                  ]

    def get_data(self, url, output):

        resp_data = {'data': []}

        while url:

            # /api/v2/accounts
            if 'https://cradlepointecm.com/api/v2/accounts/' in url:
                url = url.replace(f'&account={args.account}', f'&id={args.account}')

            with requests.Session() as s:

                retries = Retry(total=self.retry_total,
                                backoff_factor=self.retry_backoff,
                                status_forcelist=self.retry_list
                                )
                a = requests.adapters.HTTPAdapter(max_retries=retries)
                s.mount('https://', a)

                try:
                    logging.info(url)
                    r = s.get(url, headers=headers,
                              timeout=30, stream=True)

                    if r.status_code != 200:
                        logging.info(str(r.status_code) + ": " + str(r.text))

                    else:
                        self.resp = json.loads(r.content.decode("utf-8"))

                        if len(self.resp['data']) < 1:
                            return self.resp

                        else:
                            for item in self.resp['data']:
                                resp_data['data'].append(item)

                            if args.page and self.resp['meta']['next']:
                                url = self.resp['meta']['next']

                            if args.steps and self.resp['meta']['next']:
                                while args.steps != 0:
                                    args.steps -= 1
                                    url = self.resp['meta']['next']
                                    break
                            else:
                                url = None

                except Exception as e:
                    logging.info("Exception:", e)
                    raise

        data = json.dumps(resp_data, indent=4, sort_keys=False)

        with open(f'json/{output}', 'w') as outfile:
            outfile.write(data)

        return data


if __name__ == '__main__':

    # Create json and logs dir
    for path in ['json', 'logs']:
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Parse commandline options.
        parser = argparse.ArgumentParser(
            description="Query APIv2 Historical Locations")

        parser.add_argument("endpoint")

        parser.add_argument("--ecm-api-id", help="Override X_ECM_API_ID")
        parser.add_argument("--ecm-api-key", help="Override X_ECM_API_KEY")
        parser.add_argument("--cp-api-id", help="Override X-CP-API-ID")
        parser.add_argument("--cp-api-key", help="Override X-CP-API-KEY")

        parser.add_argument(
            "--account", help="Your NCM ID found NCM in settings.")

        parser.add_argument(
            "--limit", help="Limit elements in reply, default is 500", default=500)

        parser.add_argument(
            "--page", action="store_true", help="Keep following the next URL."
        )
        parser.add_argument(
            "--server", default="https://cradlepointecm.com", help="Base URL of server"
        )
        parser.add_argument(
            "--steps", type=int, help="If --walk, Walk only this many steps.", default=-1
        )
        parser.add_argument(
            "--output", help="json output file name and location", default='example.json'
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

        if args.endpoint in endpoints:
            url = f"{args.server}/api/v2/{args.endpoint}/"
        else:
            logging.info('Choose a valid endpoint.')
            sys.exit()

        if args.limit:
            url += f"?limit={args.limit}"
        if args.account:
            url += f"&account={args.account}"
        if args.output:
            output = args.output

    except Exception as e:
        logging.info(e)
        raise

    logging.info('Started')

    # Create an instance of the class
    session = NCM_APIv2()
    logging.info(session)

    # Call the get routers function from the instance of the class
    data = session.get_data(f'{url}', f'{output}')

    logging.info('Finished')
