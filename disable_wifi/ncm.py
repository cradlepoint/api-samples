"""
NCM_API.py contains a class for interacting with router configurations using the NCM APIv2

Made by Harvey Breaux for use with Cradlepoint APIv2
"""

import requests
import json


class RouterConfig(object):
    """
    The RouterConfig class is a mechanism to make communicating with the NCM APIv2 simpler.  Instances of this class
    use the requests library to communicate with the NCM APIv2.
    """

    def __init__(self, headers):
        """
        A dictionary of your NCM API Headers is required.  These are necessary to communicate with the NCM API.
        These headers have to be generated from your NetCloud Manager account.

        Header format: {
            'X-CP-API-ID': 'Your api ID',
            'X-CP-API-KEY': 'Your api key',
            'X-ECM-API-ID': 'Your ecm api ID',
            'X-ECM-API-KEY': 'Your ecm api key',
            'Content-Type': 'application/json'
        }
        """
        self.headers = headers

    def get(self, router_ids):
        """
        Sends a get request to retrieve the configuration of one or multiple routers in NCM.

        Args:
            router_ids: router_ids: A list of NCM router ids.  You can view these IDs on the devices page in NCM

        Returns:
            A dictionary containing the response information.  The dictionary is structured so the keys = Router ID,
            and the value = The response for that Router ID
        """
        # turn our list of router ids into a list of configuration_manager uris
        config_url_list = self.get_config_urls(router_ids)
        response = {}
        response_number = 0

        # open a session to NCM
        with requests.Session() as s:
            s.headers.update(self.headers)

            # get configuration for every router and store the response in a dictionary
            for url in config_url_list:
                try:
                    # get the configuration for the router
                    get = s.get(url)
                    # store the response
                    response[router_ids[response_number]] = get
                    response_number += 1

                except Exception as e:
                    print('Exception in get(): %s' + str(e) % router_ids[response_number])
                    response_number += 1

        return response

    def put(self, router_ids, payload):
        """
        Puts a configuration to one or multiple routers in NCM. A Put will replace the entire config with the payload
        you send.  If you want to add to the configuration instead of replace all of it, you should use a patch instead.

        Args:
            router_ids: router_ids: A list of NCM router ids.  You can view these IDs on the devices page in NCM
            payload: The json configuration you want to put.

        Returns:
            A dictionary containing the response information.  The dictionary is structured so the keys = Router ID,
            and the value = The response for that Router ID
        """
        # turn our router ids into a list of configuration_manager uris
        config_url_list = self.get_config_urls(router_ids)
        response = {}
        response_number = 0

        # open a session to NCM
        with requests.Session() as s:
            s.headers.update(self.headers)

            # put payload to every configuration manager uri and store the response in a dictionary
            for url in config_url_list:
                try:
                    # put the payload to the router
                    put = s.put(url, data=json.dumps(payload))
                    # store the response
                    response[router_ids[response_number]] = put
                    response_number += 1

                except Exception as e:
                    print('Exception in put() with %s: ' + str(e) % router_ids[response_number])
                    response_number += 1

        return response

    def patch(self, router_ids, payload):
        """
        Patch a configuration to a router in NCM. A patch adds your json payload to the routers config.
        Unlike a put, a patch will not remove the rest of the config that isn't in the payload.

        Args:
            router_ids: router_ids: A list of NCM router ids.  You can view these IDs on the devices page in NCM
            payload: The json configuration you want to put.

        Returns:
            A dictionary containing the response information.  The dictionary is structured so the keys = Router ID,
            and the value = The response for that Router ID
        """
        # turn our router ids into a list of configuration_manager uris
        config_url_list = self.get_config_urls(router_ids)
        response = {}
        response_number = 0

        # open a session to NCM
        with requests.Session() as s:
            s.headers.update(self.headers)

            # patch payload to every configuration manager uri
            for url in config_url_list:
                try:
                    # patch payload to the router
                    patch = requests.patch(url, data=json.dumps(payload), headers=self.headers)
                    # store the response
                    response[router_ids[response_number]] = patch
                    response_number += 1

                except Exception as e:
                    print('Exception in patch() with %s: ' + str(e) % router_ids[response_number])
                    response_number += 1

        return response

    def get_config_urls(self, router_ids):
        """
        This is a method that gets the configuration manager uris for a given router id. It is used by get(), put(),
        and patch() to communicate with the configuration_managers endpoint for your routers.  It can be used on its
        own to get a list configuration managers endpoints for a given list of router IDs.

        Args:
            router_ids: router_ids: A list of NCM router ids.  You can view these IDs on the devices page in NCM.

        Returns:
            A list of the configuration manager URIs for the router IDs given.
        """
        # ensure router ids is a list, if not make it one
        self.make_list(router_ids)
        config_url_list = []

        # open a session to NCM
        with requests.Session() as s:
            s.headers.update(self.headers)

            try:
                for router_id in router_ids:
                    # Access the routers endpoint for the router
                    url = "https://www.cradlepointecm.com/api/v2/routers/{}/".format(router_id)
                    routers = s.get(url)
                    # extract the configuration_manager id url
                    url = routers.json()['configuration_manager']

                    # do a get on the configuration_manager so that we can extract the configuration_managers url
                    config_id = s.get(url)
                    # append the configuration_managers url(the resource uri) to our config_url_list
                    config_url_list.append(config_id.json()["resource_uri"])

            except Exception as e:
                print(e)

        return config_url_list

    @staticmethod
    def make_list(router_ids):
        # Checks if router_ids is list, and tries to split it into a list if it isn't.
        if isinstance(router_ids, list):
            return router_ids
        else:
            return router_ids.split()
