"""
Cradlepoint NCM API class
Created by: Nathan Wiens

Overview:
    The purpose of this class is to make it easier for users to interact with
    the Cradlepoint NCM API. Within this class is a set of functions that
    closely matches the available API calls. Full documentation of the
    Cradlepoint NCM API is available at https://developer.cradlepoint.com.

Requirements:
    A set of Cradlepoint NCM API Keys is required to make API calls.
    While the class can be instantiated without supplying API keys,
    any subsequent calls will fail unless the keys are set via the
    set_api_keys() method.

Usage:
    Instantiating the class:
        import ncm
        api_keys = {
           'X-CP-API-ID': 'b89a24a3',
           'X-CP-API-KEY': '4b1d77fe271241b1cfafab993ef0891d',
           'X-ECM-API-ID': 'c71b3e68-33f5-4e69-9853-14989700f204',
           'X-ECM-API-KEY': 'f1ca6cd41f326c00e23322795c063068274caa30'
        }
        n = ncm.NcmClient(api_keys=api_keys)

    Example API call:
        n.get_accounts()

Tips:
    This python class includes a few optimizations to make it easier to
    work with the API. The default record limit is set at 500 instead of
    the Cradlepoint default of 20, which reduces the number of API calls
    required to return large sets of data.

    This can be modified by specifying a "limit parameter":
       n.get_accounts(limit=10)

    You can also return the full list of records in a single array without
    the need for paging by passing limit='all':
       n.get_accounts(limit='all')

    It also has native support for handling any number of "__in" filters
    beyond Cradlepoint's limit of 100. The script automatically chunks
    the list into groups of 100 and combines the results into a single array.
"""

from requests import Session
from requests.adapters import HTTPAdapter
from http import HTTPStatus
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import os
import json


def __is_json(test_json):
    """
    Checks if a string is a valid json object
    """
    try:
        json.loads(test_json)
    except ValueError:
        return False
    return True


class NcmClient:
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __init__(self,
                 api_keys=None,
                 log_events=True,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=os.environ.get(
                     'CP_BASE_URL', 'https://www.cradlepointecm.com/api/v2')
                 ):
        """
        Constructor. Sets up and opens request session.
        :param api_keys: Dictionary of API credentials.
          Optional, but must be set before calling functions.
        :type api_keys: dict
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries.
          Optional.
        :param retry_on: types of errors on which automatic retry will occur.
          Optional.
        :param base_url: # base url for calls. Configurable for testing.
          Optional.
        """
        if retry_on is None:
            retry_on = [
                HTTPStatus.REQUEST_TIMEOUT,
                HTTPStatus.GATEWAY_TIMEOUT,
                HTTPStatus.SERVICE_UNAVAILABLE
            ]
        if api_keys is None:
            api_keys = {}
        self.logEvents = log_events
        self.base_url = base_url
        self.session = Session()
        self.adapter = HTTPAdapter(
            max_retries=Retry(total=retries,
                              backoff_factor=retry_backoff_factor,
                              status_forcelist=retry_on,
                              redirect=3
                              )
        )
        self.session.mount(self.base_url, self.adapter)
        if api_keys:
            if self.__validate_api_keys(api_keys):
                self.session.headers.update(api_keys)
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def __return_handler(self, status_code, returntext, obj_type):
        """
        Prints returned HTTP request information if self.logEvents is True.
        """
        if str(status_code) == '200':
            if self.logEvents:
                print('{0} Operation Successful\n'.format(str(obj_type)))
            return None
        elif str(status_code) == '201':
            if self.logEvents:
                print('{0} Added Successfully\n'.format(str(obj_type)))
            return None
        elif str(status_code) == '202':
            if self.logEvents:
                print('{0} Added Successfully\n'.format(str(obj_type)))
            return None
        elif str(status_code) == '204':
            if self.logEvents:
                print('{0} Deleted Successfully\n'.format(str(obj_type)))
            return None
        elif str(status_code) == '400':
            if self.logEvents:
                print('Bad Request\n')
            return None
        elif str(status_code) == '401':
            if self.logEvents:
                print('Unauthorized Access\n')
            return returntext
        elif str(status_code) == '404':
            if self.logEvents:
                print('Resource Not Found\n')
            return returntext
        elif str(status_code) == '500':
            if self.logEvents:
                print('HTTP 500 - Server Error\n')
            return returntext
        else:
            print('HTTP Status Code: {0} - No returned data\n'.format(
                str(status_code)))

    def __get_json(self, get_url, call_type, params=None):
        """
        Returns full paginated results, and handles chunking "__in" params
        in groups of 100.
        """
        results = []
        __in_keys = 0
        if params['limit'] == 'all':
            params['limit'] = 1000000
        limit = int(params['limit'])

        if params is not None:
            # Ensures that order_by is passed as a comma separated string
            if 'order_by' in params.keys():
                if type(params['order_by']) is list:
                    params['order_by'] = ','.join(
                        str(x) for x in params['order_by'])
                elif type(params['order_by']) is not list and type(
                        params['order_by']) is not str:
                    raise TypeError(
                        "Invalid 'order_by' parameter. "
                        "Must be 'list' or 'str'.")

            for key, val in params.items():
                # Handles multiple filters using __in fields.
                if '__in' in key:
                    __in_keys += 1
                    # Cradlepoint limit of 100 values.
                    # If more than 100 values, break into chunks
                    chunks = self.__chunk_param(val)
                    # For each chunk, get the full results list and
                    # filter by __in parameter
                    for chunk in chunks:
                        # Handles a list of int or list of str
                        chunk_str = ','.join(map(str, chunk))
                        params.update({key: chunk_str})
                        url = get_url
                        while url and (len(results) < limit):
                            ncm = self.session.get(url, params=params)
                            if not (200 <= ncm.status_code < 300):
                                break
                            self.__return_handler(ncm.status_code,
                                                  ncm.json()['data'],
                                                  call_type)
                            url = ncm.json()['meta']['next']
                            for d in ncm.json()['data']:
                                results.append(d)

        if __in_keys == 0:
            url = get_url
            while url and (len(results) < limit):
                ncm = self.session.get(url, params=params)
                if not (200 <= ncm.status_code < 300):
                    break
                self.__return_handler(ncm.status_code, ncm.json()['data'],
                                      call_type)
                url = ncm.json()['meta']['next']
                for d in ncm.json()['data']:
                    results.append(d)
        return results

    def __parse_kwargs(self, kwargs, allowed_params):
        """
        Increases default return limit to 500,
        and checks for invalid parameters
        """
        params = {k: v for (k, v) in kwargs.items() if k in allowed_params}
        if 'limit' not in params:
            params.update({'limit': '500'})

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'X-CP-API-ID' not in self.session.headers:
            raise KeyError(
                "X-CP-API-ID missing. "
                "Please ensure all API Keys are present.")

        if 'X-CP-API-KEY' not in self.session.headers:
            raise KeyError(
                "X-CP-API-KEY missing. "
                "Please ensure all API Keys are present.")

        if 'X-ECM-API-ID' not in self.session.headers:
            raise KeyError(
                "X-ECM-API-ID missing. "
                "Please ensure all API Keys are present.")

        if 'X-ECM-API-KEY' not in self.session.headers:
            raise KeyError(
                "X-ECM-API-KEY missing. "
                "Please ensure all API Keys are present.")

        return params

    @staticmethod
    def __chunk_param(param):
        """
        Chunks parameters into groups of 100 per Cradlepoint limit.
        Iterate through chunks with a for loop.
        """
        n = 100

        if type(param) is str:
            param_list = param.split(",")
        elif type(param) is list:
            param_list = param
        else:
            raise TypeError("Invalid param format. Must be str or list.")

        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(param_list), n):
            yield param_list[i:i + n]

    @staticmethod
    def __validate_api_keys(api_keys):
        """
        Checks NCM API Keys are a dictionary containing all necessary keys
        :param api_keys: Dictionary of API credentials. Optional.
        :type api_keys: dict
        :return: True if valid
        """
        if type(api_keys) is not dict:
            raise TypeError("API Keys must be passed as a dictionary")

        if 'X-CP-API-ID' not in api_keys:
            raise KeyError(
                "X-CP-API-ID missing. "
                "Please ensure all API Keys are present.")

        if 'X-CP-API-KEY' not in api_keys:
            raise KeyError(
                "X-CP-API-KEY missing. "
                "Please ensure all API Keys are present.")

        if 'X-ECM-API-ID' not in api_keys:
            raise KeyError(
                "X-ECM-API-ID missing. "
                "Please ensure all API Keys are present.")

        if 'X-ECM-API-KEY' not in api_keys:
            raise KeyError(
                "X-ECM-API-KEY missing. "
                "Please ensure all API Keys are present.")
        return True

    def set_api_keys(self, api_keys):
        """
        Sets NCM API Keys for session.
        :param api_keys: Dictionary of API credentials. Optional.
        :type api_keys: dict
        """
        if self.__validate_api_keys(api_keys):
            self.session.headers.update(api_keys)
        return

    def get_accounts(self, **kwargs):
        """
        Returns accounts with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of accounts based on API Key.
        """
        call_type = 'Accounts'
        get_url = '{0}/accounts/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'id', 'id__in', 'name',
                          'name__in', 'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_account_by_id(self, account_id):
        """
        This method returns a single account for a given account id.
        :param account_id: ID of account to return
        :return:
        """
        return self.get_accounts(id=account_id)[0]

    def get_account_by_name(self, account_name):
        """
        This method returns a single account for a given account name.
        :param account_name: Name of account to return
        :return:
        """

        return self.get_accounts(name=account_name)[0]

    def create_subaccount_by_parent_id(self, parent_account_id,
                                       subaccount_name):
        """
        This operation creates a new subaccount.
        :param parent_account_id: ID of parent account.
        :param subaccount_name: Name for new subaccount.
        :return:
        """
        call_type = 'Subaccount'
        post_url = '{0}/accounts/'.format(self.base_url)

        post_data = {
            'account': '/api/v1/accounts/{}/'.format(str(parent_account_id)),
            'name': str(subaccount_name)
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_subaccount_by_parent_name(self, parent_account_name,
                                         subaccount_name):
        """
        This operation creates a new subaccount.
        :param parent_account_name: Name of parent account.
        :param subaccount_name: Name for new subaccount.
        :return:
        """
        return self.create_subaccount_by_parent_id(self.get_account_by_name(
            parent_account_name)['id'], subaccount_name)

    def rename_subaccount_by_id(self, subaccount_id, new_subaccount_name):
        """
        This operation renames a subaccount
        :param subaccount_id: ID of subaccount to rename
        :param new_subaccount_name: New name for subaccount
        :return:
        """
        call_type = 'Subaccount'
        put_url = '{0}/accounts/{1}/'.format(self.base_url, str(subaccount_id))

        put_data = {
            "name": str(new_subaccount_name)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def rename_subaccount_by_name(self, subaccount_name, new_subaccount_name):
        """
        This operation renames a subaccount
        :param subaccount_name: Name of subaccount to rename
        :param new_subaccount_name: New name for subaccount
        :return:
        """
        return self.rename_subaccount_by_id(self.get_account_by_name(
            subaccount_name)['id'], new_subaccount_name)

    def delete_subaccount_by_id(self, subaccount_id):
        """
        This operation deletes a subaccount
        :param subaccount_id: ID of subaccount to delete
        :return:
        """
        call_type = 'Subaccount'
        post_url = '{0}/accounts/{1}'.format(self.base_url, subaccount_id)

        ncm = self.session.delete(post_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def delete_subaccount_by_name(self, subaccount_name):
        """
        This operation deletes a subaccount
        :param subaccount_name: Name of subaccount to delete
        :return:
        """
        return self.delete_subaccount_by_id(self.get_account_by_name(
            subaccount_name)['id'])

    def get_activity_logs(self, **kwargs):
        """
        This method returns NCM activity log information.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Activity Logs'
        get_url = '{0}/activity_logs/'.format(self.base_url)

        allowed_params = ['account', 'created_at__exact', 'created_at__lt',
                          'created_at__lte', 'created_at__gt',
                          'created_at__gte', 'action__timestamp__exact',
                          'action__timestamp__lt',
                          'action__timestamp__lte', 'action__timestamp__gt',
                          'action__timestamp__gte', 'actor__id',
                          'object__id', 'action__id__exact', 'actor__type',
                          'action__type', 'object__type', 'order_by',
                          'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_alerts(self, **kwargs):
        """
        This method gives alert information with associated id.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Alerts'
        get_url = '{0}/alerts/'.format(self.base_url)

        allowed_params = ['account', 'created_at', 'created_at_timeuuid',
                          'detected_at', 'friendly_info', 'info',
                          'router', 'type', 'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_configuration_managers(self, **kwargs):
        """
        A configuration manager is an abstract resource for controlling and
        monitoring config sync on a single device.
        Each device has its own corresponding configuration manager.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Configuration Managers'
        get_url = '{0}/configuration_managers/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'fields', 'id', 'id__in',
                          'router', 'router__in', 'synched',
                          'suspended', 'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_configuration_manager_id(self, router_id, **kwargs):
        """
        A configuration manager is an abstract resource for controlling and
        monitoring config sync on a single device.
        Each device has its own corresponding configuration manager.
        :param router_id: Router ID to query
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Configuration Managers'
        get_url = '{0}/configuration_managers/?router.id={1}&fields=id'.format(
            self.base_url, router_id)

        allowed_params = ['account', 'account__in', 'id', 'id__in', 'router',
                          'router__in', 'synched',
                          'suspended', 'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)[0]['id']

    def update_configuration_managers(self, config_man_id, config_man_json):
        """
        This method updates an configuration_managers for associated id.
        :param config_man_id: ID of the Configuration Manager to modify
        :param config_man_json: JSON of the "configuration" field of the
          configuration manager
        :return:
        """
        call_type = 'Configuration Manager'
        put_url = '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                           config_man_id)

        ncm = self.session.put(put_url, json=config_man_json)
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def patch_configuration_managers(self, router_id, config_man_json):
        """
        This method patches an configuration_managers for associated id.
        :param router_id: ID of router to update
        :param config_man_json: JSON of the "configuration" field of the
          configuration manager
        :return:
        """
        call_type = 'Configuration Manager'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID for router
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = config_man_json

        ncm = self.session.patch(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(config_man_id)),
            data=json.dumps(payload))  # Patch indie config with new values

        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def put_configuration_managers(self, router_id, configman_json):
        """
        This method overwrites the configuration for a router with id.
        :param router_id: ID of router to update
        :param configman_json: JSON of the "configuration" field of the
          configuration manager
        :return:
        """
        call_type = 'Configuration Manager'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID for router
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        configman_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = configman_json

        ncm = self.session.put(
            '{0}/configuration_managers/{1}/?fields=configuration'.format(
                self.base_url, str(configman_id)),
            json=payload)  # Patch indie config with new values
        result = self.__returnhandler(ncm.status_code, ncm.text, call_type)
        return result

    def patch_group_configuration(self, group_id, config_json):
        """
        This method patches an configuration_managers for associated id.
        :param group_id: ID of group to update
        :param config_json: JSON of the "configuration" field of the
          configuration manager
        :return:
        """
        call_type = 'Configuration Manager'

        payload = config_json

        ncm = self.session.patch(
            '{0}/groups/{1}/'.format(self.base_url, str(group_id)),
            data=json.dumps(payload))  # Patch indie config with new values
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def copy_router_configuration(self, src_router_id, dst_router_id):
        """
        Copies the Configuration Manager config of one router to another.
        This function will not copy any passwords as they are encrypted.
        :param src_router_id: Router ID to copy from
        :param dst_router_id: Router ID to copy to
        :return: Should return HTTP Status Code 202 if successful
        """
        call_type = 'Configuration Manager'
        """Get source router existing configuration"""
        src_config = self.get_configuration_managers(router=src_router_id,
                                                     fields='configuration')[0]

        """Strip passwords which aren't stored in plain text"""
        src_config = json.dumps(src_config).replace(', "wpapsk": "*"',
                                                    '').replace(
            '"wpapsk": "*"', '') \
            .replace(', "password": "*"', '').replace('"password": "*"', '')

        """Get destination router Configuration Manager ID"""
        dst_config_man_id = \
            self.get_configuration_managers(router=dst_router_id)[0]['id']

        put_url = '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                           dst_config_man_id)

        ncm = self.session.patch(put_url, data=src_config)
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def resume_updates_for_router(self, router_id):
        """
        This method will resume updates for a router in Sync Suspended state.
        :param router_id: ID of router to update
        :return:
        """
        call_type = 'Configuration Manager'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID for router
        response = json.loads(response.content.decode("utf-8"))
        configman_id = response['data'][0]['id']
        payload = {"suspended": False}

        ncm = self.session.put(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(configman_id)),
            json=payload)
        result = self.__returnhandler(ncm.status_code, ncm.text, call_type)
        return result

    def get_device_app_bindings(self, **kwargs):
        """
        This method gives device app binding information for all device
        app bindings associated with the account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Device App Bindings'
        get_url = '{0}/device_app_bindings/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'group', 'group__in',
                          'app_version', 'app_version__in',
                          'id', 'id__in', 'state', 'state__in', 'expand',
                          'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_device_app_states(self, **kwargs):
        """
        This method gives device app state information for all device
        app states associated with the account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Device App States'
        get_url = '{0}/device_app_states/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'router', 'router__in',
                          'app_version', 'app_version__in',
                          'id', 'id__in', 'state', 'state__in', 'expand',
                          'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_device_app_versions(self, **kwargs):
        """
        This method gives device app version information for all device
        app versions associated with the account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Device App Versions'
        get_url = '{0}/device_app_versions/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'app', 'app__in', 'id',
                          'id__in', 'state', 'state__in',
                          'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_device_apps(self, **kwargs):
        """
        This method gives device app information for all device apps
        associated with the account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Device Apps'
        get_url = '{0}/device_apps/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'name', 'name__in', 'id',
                          'id__in', 'uuid', 'uuid__in',
                          'expand', 'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_failovers(self, **kwargs):
        """
        This method returns a list of Failover Events for
        a device, group, or account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Failovers'
        get_url = '{0}/failovers/'.format(self.base_url)

        allowed_params = ['account_id', 'group_id', 'router_id', 'started_at',
                          'ended_at', 'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_firmwares(self, **kwargs):
        """
        This operation gives the list of device firmwares.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Firmwares'
        get_url = '{0}/firmwares/'.format(self.base_url)

        allowed_params = ['id', 'id__in', 'version', 'version__in', 'limit',
                          'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_firmware_for_product_id_by_version(self, product_id,
                                               firmware_name):
        """
        This operation returns firmwares for a given model ID and version name.
        :param product_id: The ID of the product (e.g. 46)
        :param firmware_name: The Firmware Version (e.g. 7.2.0)
        :return:
        """
        for f in self.get_firmwares(version=firmware_name):
            if f['product'] == '{0}/products/{1}/'.format(self.base_url,
                                                          str(product_id)):
                return f
        raise ValueError("Invalid Firmware Version")

    def get_firmware_for_product_name_by_version(self, product_name,
                                                 firmware_name):
        """
        This operation returns firmwares for a given model and version name.
        :param product_name: The Name of the product (e.g. IBR200)
        :param firmware_name: The Firmware Version (e.g. 7.2.0)
        :return:
        """
        product_id = self.get_product_by_name(product_name)['id']
        return self.get_firmware_for_product_id_by_version(product_id,
                                                           firmware_name)

    def get_groups(self, **kwargs):
        """
        This method gives a groups list.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Groups'
        get_url = '{0}/groups/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'id', 'id__in', 'name',
                          'name__in', 'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_group_by_id(self, group_id):
        """
        This method returns a single group.
        :param group_id: The ID of the group.
        :return:
        """
        return self.get_groups(id=group_id)[0]

    def get_group_by_name(self, group_name):
        """
        This method returns a single group.
        :param group_name: The Name of the group.
        :return:
        """
        return self.get_groups(name=group_name)[0]

    def create_group_by_parent_id(self, parent_account_id, group_name,
                                  product_name, firmware_version):
        """
        This operation creates a new group.
        :param parent_account_id: ID of parent account
        :param group_name: Name for new group
        :param product_name: Product model (e.g. IBR200)
        :param firmware_version: Firmware version for group (e.g. 7.2.0)
        :return:
        Example: n.create_group_by_parent_id('123456', 'My New Group',
            'IBR200', '7.2.0')
        """

        call_type = 'Group'
        post_url = '{0}/groups/'.format(self.base_url)

        firmware = self.get_firmware_for_product_name_by_version(
            product_name, firmware_version)

        post_data = {
            'account': '/api/v1/accounts/{}/'.format(str(parent_account_id)),
            'name': str(group_name),
            'product': str(
                self.get_product_by_name(product_name)['resource_url']),
            'target_firmware': str(firmware['resource_url'])
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_group_by_parent_name(self, parent_account_name, group_name,
                                    product_name, firmware_version):
        """
        This operation creates a new group.
        :param parent_account_name: Name of parent account
        :param group_name: Name for new group
        :param product_name: Product model (e.g. IBR200)
        :param firmware_version: Firmware version for group (e.g. 7.2.0)
        :return:
        Example: n.create_group_by_parent_name('Parent Account',
            'My New Group', 'IBR200', '7.2.0')
        """

        return self.create_group_by_parent_id(
            self.get_account_by_name(parent_account_name)['id'], group_name,
            product_name, firmware_version)

    def rename_group_by_id(self, group_id, new_group_name):
        """
        This operation renames a group by specifying ID.
        :param group_id: ID of the group to rename.
        :param new_group_name: New name for the group.
        :return:
        """
        call_type = 'Group'
        put_url = '{0}/groups/{1}/'.format(self.base_url, group_id)

        put_data = {
            "name": str(new_group_name)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def rename_group_by_name(self, existing_group_name, new_group_name):
        """
        This operation renames a group by specifying name.
        :param existing_group_name: Name of the group to rename
        :param new_group_name: New name for the group.
        :return:
        """
        return self.rename_group_by_id(
            self.get_group_by_name(existing_group_name)['id'], new_group_name)

    def delete_group_by_id(self, group_id):
        """
        This operation deletes a group by specifying ID.
        :param group_id: ID of the group to delete
        :return:
        """
        call_type = 'Group'
        post_url = '{0}/groups/{1}/'.format(self.base_url, group_id)

        ncm = self.session.delete(post_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def delete_group_by_name(self, group_name):
        """
        This operation deletes a group by specifying Name.
        :param group_name: Name of the group to delete
        :return:
        """
        return self.delete_group_by_id(
            self.get_group_by_name(group_name)['id'])

    def get_historical_locations(self, router_id, **kwargs):
        """
        This method returns a list of locations visited by a device.
        :param router_id: ID of the router
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Historical Locations'
        get_url = '{0}/historical_locations/?router={1}'.format(self.base_url,
                                                                router_id)

        allowed_params = ['created_at__gt', 'created_at_timeuuid__gt',
                          'created_at__lte', 'fields', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_historical_locations_for_date(self, router_id, date,
                                          tzoffset_hrs=0, limit='all',
                                          **kwargs):
        """
        This method provides a history of device alerts.
        To receive device alerts, you must enable them through the NCM UI:
        Alerts -> Settings. The info section of the alert is firmware dependent
        and may change between firmware releases.
        :param router_id: ID of the router
        :param date: Date to filter logs. Must be in format "YYYY-mm-dd"
        :type date: str
        :param tzoffset_hrs: Offset from UTC for local timezone
        :type tzoffset_hrs: int
        :param limit: Number of records to return.
          Specifying "all" returns all records. Default all.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """

        d = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=tzoffset_hrs)
        start = d.strftime("%Y-%m-%dT%H:%M:%S")
        end = (d + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        call_type = 'Historical Locations'
        get_url = '{0}/historical_locations/?router={1}'.format(self.base_url,
                                                                router_id)

        allowed_params = ['created_at__gt', 'created_at_timeuuid__gt',
                          'created_at__lte', 'fields', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        params.update({'created_at__lte': end,
                       'created_at__gt': start,
                       'limit': limit})

        return self.__get_json(get_url, call_type, params=params)

    def get_locations(self, **kwargs):
        """
        This method gives a list of locations.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Locations'
        get_url = '{0}/locations/'.format(self.base_url)

        allowed_params = ['id', 'id__in', 'router', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def create_location(self, account_id, latitude, longitude, router_id):
        """
        This method creates a location and applies it to a router.
        :param account_id: Account which owns the object
        :param latitude: A device's relative position north or south
        on the Earth's surface, in degrees from the Equator
        :param longitude: A device's relative position east or west
        on the Earth's surface, in degrees from the prime meridian
        :param router_id: Device that the location is associated with
        :return:
        """

        call_type = 'Locations'
        post_url = '{0}/locations/'.format(self.base_url)

        post_data = {
            'account':
                'https://www.cradlepointecm.com/api/v2/accounts/{}/'.format(
                    str(account_id)),
            'accuracy': 0,
            'latitude': latitude,
            'longitude': longitude,
            'method': 'manual',
            'router': 'https://www.cradlepointecm.com/api/v2/routers/{}/'
                .format(str(router_id))
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_location_for_router(self, router_id):
        """
        This operation deletes the location for a router by ID.
        :param router_id: ID of router for which to remove location.
        :return:
        """
        call_type = 'Locations'

        locations = self.get_locations(router=router_id)
        if locations:
            location_id = locations[0]['id']

            post_url = '{0}/locations/{1}/'.format(self.base_url, location_id)

            ncm = self.session.delete(post_url)
            result = self.__return_handler(ncm.status_code, ncm.text,
                                           call_type)
            return result
        else:
            return "NO LOCATION FOUND"

    def get_net_device_health(self, **kwargs):
        """
        This operation gets cellular heath scores, by device.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Net Device Health'
        get_url = '{0}/net_device_health/'.format(self.base_url)

        allowed_params = ['net_device']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_net_device_metrics(self, **kwargs):
        """
        This endpoint is supplied to allow easy access to the latest signal and
          usage data reported by an account’s net_devices without querying the
          historical raw sample tables, which are not optimized for a query
          spanning many net_devices at once.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Net Device Metrics'
        get_url = '{0}/net_device_metrics/'.format(self.base_url)

        allowed_params = ['net_device', 'net_device__in', 'update_ts__lt',
                          'update_ts__gt', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_net_devices_metrics_for_wan(self, **kwargs):
        """
        This endpoint is supplied to allow easy access to the latest signal and
          usage data reported by an account’s net_devices without querying the
          historical raw sample tables, which are not optimized for a query
          spanning many net_devices at once. Returns data only for
          WAN interfaces.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        ids = []
        for net_device in self.get_net_devices(mode='wan'):
            ids.append(net_device['id'])
        idstring = ','.join(str(x) for x in ids)
        return self.get_net_device_metrics(net_device__in=idstring, **kwargs)

    def get_net_devices_metrics_for_mdm(self, **kwargs):
        """
        This endpoint is supplied to allow easy access to the latest signal and
          usage data reported by an account’s net_devices without querying the
          historical raw sample tables, which are not optimized for a query
          spanning many net_devices at once. Returns data only for
          modem interfaces.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        ids = []
        for net_device in self.get_net_devices(is_asset=True):
            ids.append(net_device['id'])
        idstring = ','.join(str(x) for x in ids)
        return self.get_net_device_metrics(net_device__in=idstring, **kwargs)

    def get_net_device_signal_samples(self, **kwargs):
        """
        This endpoint is supplied to allow easy access to the latest signal and
          usage data reported by an account’s net_devices without querying the
          historical raw sample tables, which are not optimized for a query
          spanning many net_devices at once.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Get Net Device Signal Samples'
        get_url = '{0}/net_device_signal_samples/'.format(self.base_url)

        allowed_params = ['net_device', 'net_device__in', 'created_at',
                          'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid', 'created_at_timeuuid__in',
                          'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte',
                          'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_net_device_usage_samples(self, **kwargs):
        """
        This method provides information about the net device's
        overall network traffic.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Net Device Usage Samples'
        get_url = '{0}/net_device_usage_samples/'.format(self.base_url)

        allowed_params = ['net_device', 'net_device__in', 'created_at',
                          'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid', 'created_at_timeuuid__in',
                          'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte',
                          'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_net_devices(self, **kwargs):
        """
        This method gives a list of net devices.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Net Devices'
        get_url = '{0}/net_devices/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'connection_state',
                          'connection_state__in', 'id', 'id__in',
                          'is_asset', 'ipv4_address', 'ipv4_address__in',
                          'mode', 'mode__in', 'router', 'router__in',
                          'expand', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_net_devices_for_router(self, router_id, **kwargs):
        """
        This method gives a list of net devices for a given router.
        :param router_id: ID of the router
        :return:
        """
        return self.get_net_devices(router=router_id, **kwargs)

    def get_net_devices_for_router_by_mode(self, router_id, mode, **kwargs):
        """
        This method gives a list of net devices for a given router,
        filtered by mode (lan/wan).
        :param router_id: ID of router
        :param mode: lan/wan
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        return self.get_net_devices(router=router_id, mode=mode, **kwargs)

    def get_products(self, **kwargs):
        """
        This method gives a list of product information.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Products'
        get_url = '{0}/products/'.format(self.base_url)

        allowed_params = ['id', 'id__in', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_product_by_id(self, product_id):
        """
        This method returns a single product by ID.
        :param product_id: ID of product (e.g. 46)
        :return:
        """
        return self.get_products(id=product_id)[0]

    def get_product_by_name(self, product_name):
        """
        This method returns a single product for a given model name.
        :param product_name: Name of product (e.g. IBR200)
        :return:
        """
        for p in self.get_products():
            if p['name'] == product_name:
                return p
        raise ValueError("Invalid Product Name")

    def reboot_device(self, router_id):
        """
        This operation reboots a device.
        :param router_id: ID of router to reboot
        :return:
        """
        call_type = 'Reboot Device'
        post_url = '{0}/reboot_activity/'.format(self.base_url)

        post_data = {
            'router': '{0}/routers/{1}/'.format(self.base_url, str(router_id))
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def reboot_group(self, group_id):
        """
        This operation reboots all routers in a group.
        :param group_id: ID of group to reboot
        :return:
        """
        call_type = 'Reboot Group'
        post_url = '{0}/reboot_activity/'.format(self.base_url)

        post_data = {
            'group': '{0}/groups/{1}/'.format(self.base_url, str(group_id))
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_router_alerts(self, **kwargs):
        """
        This method provides a history of device alerts. To receive device
        alerts, you must enable them through the ECM UI: Alerts -> Settings.
        The info section of the alert is firmware dependent and
        may change between firmware releases.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Router Alerts'
        get_url = '{0}/router_alerts/'.format(self.base_url)

        allowed_params = ['router', 'router__in', 'created_at',
                          'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid', 'created_at_timeuuid__in',
                          'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte',
                          'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_router_alerts_last_24hrs(self, tzoffset_hrs=0, **kwargs):
        """
        This method provides a history of device alerts.
        To receive device alerts, you must enable them through the NCM UI:
        Alerts -> Settings. The info section of the alert is firmware dependent
        and may change between firmware releases.
        :param tzoffset_hrs: Offset from UTC for local timezone
        :type tzoffset_hrs: int
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        d = datetime.utcnow() + timedelta(hours=tzoffset_hrs)
        end = d.strftime("%Y-%m-%dT%H:%M:%S")
        start = (d - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        call_type = 'Router Alerts'
        get_url = '{0}/router_alerts/'.format(self.base_url)

        allowed_params = ['router', 'router__in']
        params = self.__parse_kwargs(kwargs, allowed_params)

        params.update({'created_at__lt': end,
                       'created_at__gt': start,
                       'order_by': 'created_at_timeuuid',
                       'limit': '500'})

        return self.__get_json(get_url, call_type, params=params)

    def get_router_alerts_for_date(self, date, tzoffset_hrs=0, **kwargs):
        """
        This method provides a history of device alerts.
        To receive device alerts, you must enable them through the NCM UI:
        Alerts -> Settings. The info section of the alert is firmware dependent
        and may change between firmware releases.
        :param date: Date to filter logs. Must be in format "YYYY-mm-dd"
        :type date: str
        :param tzoffset_hrs: Offset from UTC for local timezone
        :type tzoffset_hrs: int
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """

        d = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=tzoffset_hrs)
        start = d.strftime("%Y-%m-%dT%H:%M:%S")
        end = (d + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        call_type = 'Router Alerts'
        get_url = '{0}/router_alerts/'.format(self.base_url)

        allowed_params = ['router', 'router__in']
        params = self.__parse_kwargs(kwargs, allowed_params)

        params.update({'created_at__lt': end,
                       'created_at__gt': start,
                       'order_by': 'created_at_timeuuid',
                       'limit': '500'})

        return self.__get_json(get_url, call_type, params=params)

    def get_router_logs(self, router_id, **kwargs):
        """
        This method provides a history of device events.
        To receive device logs you must enable them on the Group settings form.
        Enabling device logs can significantly increase the ECM network traffic
        from the device to the server depending on how quickly the device is
        generating events.
        :param router_id: ID of router from which to grab logs.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Router Logs'
        get_url = '{0}/router_logs/?router={1}'.format(self.base_url,
                                                       router_id)

        allowed_params = ['created_at', 'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid',
                          'created_at_timeuuid__in', 'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte', 'order_by', 'limit',
                          'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_router_logs_last_24hrs(self, router_id, tzoffset_hrs=0):
        """
        This method provides a history of device events.
        To receive device logs you must enable them on the Group settings form.
        Enabling device logs can significantly increase the ECM network traffic
        from the device to the server depending on how quickly the device is
        generating events.
        :param router_id: ID of router from which to grab logs.
        :param tzoffset_hrs: Offset from UTC for local timezone
        :type tzoffset_hrs: int
        :return:
        """
        d = datetime.utcnow() + timedelta(hours=tzoffset_hrs)
        end = d.strftime("%Y-%m-%dT%H:%M:%S")
        start = (d - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        call_type = 'Router Logs'
        get_url = '{0}/router_logs/?router={1}'.format(self.base_url,
                                                       router_id)

        params = {'created_at__lt': end, 'created_at__gt': start,
                  'order_by': 'created_at_timeuuid', 'limit': '500'}

        return self.__get_json(get_url, call_type, params=params)

    def get_router_logs_for_date(self, router_id, date, tzoffset_hrs=0):
        """
        This method provides a history of device events.
        To receive device logs you must enable them on the Group settings form.
        Enabling device logs can significantly increase the ECM network traffic
        from the device to the server depending on how quickly the device is
        generating events.
        :param router_id: ID of router from which to grab logs.
        :param date: Date to filter logs. Must be in format "YYYY-mm-dd"
        :type date: str
        :param tzoffset_hrs: Offset from UTC for local timezone
        :type tzoffset_hrs: int
        :return:
        """

        d = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=tzoffset_hrs)
        start = d.strftime("%Y-%m-%dT%H:%M:%S")
        end = (d + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        call_type = 'Router Logs'
        get_url = '{0}/router_logs/?router={1}'.format(self.base_url,
                                                       router_id)

        params = {'created_at__lt': end, 'created_at__gt': start,
                  'order_by': 'created_at_timeuuid', 'limit': '500'}

        return self.__get_json(get_url, call_type, params=params)

    def get_router_state_samples(self, **kwargs):
        """
        This method provides information about the connection state of the
        device with the NCM server.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Router State Samples'
        get_url = '{0}/router_state_samples/'.format(self.base_url)

        allowed_params = ['router', 'router__in', 'created_at',
                          'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid', 'created_at_timeuuid__in',
                          'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte',
                          'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_router_stream_usage_samples(self, **kwargs):
        """
        This method provides information about the connection state of the
        device with the NCM server.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Router Stream Usage Samples'
        get_url = '{0}/router_stream_usage_samples/'.format(self.base_url)

        allowed_params = ['router', 'router__in', 'created_at',
                          'created_at__lt', 'created_at__gt',
                          'created_at_timeuuid', 'created_at_timeuuid__in',
                          'created_at_timeuuid__gt',
                          'created_at_timeuuid__gte',
                          'created_at_timeuuid__lt',
                          'created_at_timeuuid__lte',
                          'order_by', 'limit', 'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_routers(self, **kwargs):
        """
        This method gives device information with associated id.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        call_type = 'Routers'
        get_url = '{0}/routers/'.format(self.base_url)

        allowed_params = ['account', 'account__in', 'device_type',
                          'device_type__in', 'group', 'group__in', 'id',
                          'id__in', 'ipv4_address', 'ipv4_address__in', 'mac',
                          'mac__in', 'name', 'name__in',
                          'reboot_required', 'reboot_required__in', 'state',
                          'state__in', 'state_updated_at__lt',
                          'state_updated_at__gt', 'updated_at__lt',
                          'updated_at__gt', 'expand', 'order_by', 'limit',
                          'offset']
        params = self.__parse_kwargs(kwargs, allowed_params)

        return self.__get_json(get_url, call_type, params=params)

    def get_router_by_id(self, router_id, **kwargs):
        """
        This method gives device information for a given router ID.
        :param router_id: ID of router
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        return self.get_routers(id=router_id, **kwargs)[0]

    def get_router_by_name(self, router_name, **kwargs):
        """
        This method gives device information for a given router name.
        :param router_name: Name of router
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        return self.get_routers(name=router_name, **kwargs)[0]

    def get_routers_for_account(self, account_id, **kwargs):
        """
        This method gives a groups list filtered by account.
        :param account_id: Account ID to filter
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        return self.get_routers(account=account_id, **kwargs)

    def get_routers_for_group(self, group_id, **kwargs):
        """
        This method gives a groups list filtered by group.
        :param group_id: Group ID to filter
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return:
        """
        return self.get_routers(group=group_id, **kwargs)

    def rename_router_by_id(self, router_id, new_router_name):
        """
        This operation renames a router by ID.
        :param router_id: ID of router to rename
        :param new_router_name: New name for router
        :return:
        """
        call_type = 'Router'
        put_url = '{0}/routers/{1}/'.format(self.base_url, router_id)

        put_data = {
            'name': str(new_router_name)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def rename_router_by_name(self, existing_router_name, new_router_name):
        """
        This operation renames a router by name.
        :param existing_router_name: Name of router to rename
        :param new_router_name: New name for router
        :return:
        """
        return self.rename_router_by_id(
            self.get_router_by_name(existing_router_name)['id'],
            new_router_name)

    def assign_router_to_group(self, router_id, group_id):
        """
        This operation assigns a router to a group.
        :param router_id: ID of router to move.
        :param group_id: ID of destination group.
        :return:
        """
        call_type = "Routers"

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "group": 'https://www.cradlepointecm.com/api/v2/groups/{}/'.format(
                group_id)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def assign_router_to_account(self, router_id, account_id):
        """
        This operation assigns a router to an account.
        :param router_id: ID of router to move.
        :param account_id: ID of destination account.
        :return:
        """
        call_type = "Routers"

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "account":
                'https://www.cradlepointecm.com/api/v2/accounts/{}/'.format(
                    account_id)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_router_by_id(self, router_id):
        """
        This operation deletes a router by ID.
        :param router_id: ID of router to delete.
        :return:
        """
        call_type = 'Router'
        post_url = '{0}/routers/{1}/'.format(self.base_url, router_id)

        ncm = self.session.delete(post_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def delete_router_by_name(self, router_name):
        """
        This operation deletes a router by name.
        :param router_name: Name of router to delete
        :return:
        """
        return self.delete_router_by_id(
            self.get_router_by_name(router_name)['id'])

    def set_lan_ip_address(self, router_id, lan_ip, netmask=None,
                           network_id=0):
        """
        This method sets the Primary LAN IP Address for a given router id.
        :param router_id: ID of router to update
        :param lan_ip: LAN IP Address. (e.g. 192.168.1.1)
        :param netmask: Subnet mask. (e.g. 255.255.255.0)
        :param network_id: The ID of the network to update.
          Numbering starts from 0.
        :return:
        """
        call_type = 'LAN IP Address'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        if netmask:
            payload = {
                "configuration": [
                    {
                        "lan": {
                            network_id: {
                                "ip_address": lan_ip,
                                "netmask": netmask
                            }
                        }
                    },
                    []
                ]
            }

        else:
            payload = {
                "configuration": [
                    {
                        "lan": {
                            network_id: {
                                "ip_address": lan_ip
                            }
                        }
                    },
                    []
                ]
            }

        ncm = self.session.patch(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(config_man_id)),
            data=json.dumps(payload))  # Patch indie config with new values
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_custom1(self, router_id, text):
        """
        This method updates the Custom1 field in NCM for a given router id.
        :param router_id: ID of router to update.
        :param text: The text to set for the field
        :return:
        """
        call_type = "NCM Field Update"

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "custom1": str(text)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def set_custom2(self, router_id, text):
        """
        This method updates the Custom2 field in NCM for a given router id.
        :param router_id: ID of router to update.
        :param text: The text to set for the field
        :return:
        """
        call_type = "NCM Field Update"

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "custom2": str(text)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result
