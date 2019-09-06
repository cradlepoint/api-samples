"""
NOTE: Cradlepoint does not develop, maintain, or support NCM API applications.
Applications are the sole responsibility of the developer.

WARNING: NCM API Applications can introduce security and other potential issues
when not carefully engineered. Test your code thoroughly before deploying it to
production devices. This can affect production devices and data!
"""

import json
import os
import requests
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime


class NCM_APIv2(object):

    headers = {
        'X-ECM-API-ID': '',
        'X-ECM-API-KEY': '',
        'X-CP-API-ID': '',
        'X-CP-API-KEY': '',
        'Accept': '*/*',
        'Content-Type': 'application/json',
    }

    def get_data(self, url, json_output):

        resp_data = {'data': []}

        while url:

            with requests.Session() as s:

                retries = Retry(total=5,  # Total number of retries to allow.
                                backoff_factor=2,
                                status_forcelist=[408,  # 408 Request Timeout
                                                  500,  # 500 Internal Server Error
                                                  502,  # 502 Bad Gateway
                                                  503,  # 503 Service Unavailable
                                                  504,  # 504 Gateway Timeout
                                                  ],
                                )
                a = requests.adapters.HTTPAdapter(max_retries=retries)
                s.mount('https://', a)

                try:
                    logging.info(url)
                    print(url)
                    r = s.get(url, headers=self.headers,
                              timeout=30, stream=True)

                    if r.status_code != 200:
                        logging.error(str(r.status_code) + ": " + str(r.text))
                        s.get('https://accounts.cradlepointecm.com/logout')

                    else:
                        self.resp = json.loads(r.content.decode("utf-8"))

                        if len(self.resp['data']) < 1:
                            logging.warning('No response data was returned.')
                            return self.resp

                        else:
                            for item in self.resp['data']:
                                resp_data['data'].append(item)

                            if self.resp['meta']['next']:
                                url = self.resp['meta']['next']
                            else:
                                url = None

                except Exception as e:
                    logging.error("Exception:", e)
                    raise

        data = json.dumps(resp_data, indent=4, sort_keys=False)

        with open(f'json/{json_output}.json', 'w') as outfile:
            outfile.write(data)
            outfile.close()

        return data


def create_dirs():

    base_path = os.getcwd()

    directorys = ['json', 'logs']

    for path in directorys:

        dir_path = os.path.join(base_path, path)

        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError:
                print (f"Creation of the directory %s failed" % dir_path)
            else:
                print ("Successfully created the directory %s " % dir_path)
        else:
            print ("%s already exists" % dir_path)


if __name__ == '__main__':

    try:
        create_dirs()

        logging.basicConfig(
            filename=f'logs/{datetime.now().strftime("%d_%m_%Y_%H_%M_%S.log")}',
            level=logging.INFO,
            format='%(asctime)s %(message)s',
        )

        logging.info('Started')

        # Create an instance of the class
        session = NCM_APIv2()

        # Call the get routers function from the instance of the class
        router_data = session.get_data(
            'https://www.cradlepointecm.com/api/v2/routers/?limit=500&offset=0', 'routers.json')

        # Call the get locations function from the instance of the class
        location_data = session.get_data(
            'https://www.cradlepointecm.com/api/v2/locations/?limit=500&offset=0', 'locations.json')

        logging.info('Finished')

    except Exception as e:
        logging.error(e)
