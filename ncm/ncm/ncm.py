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
    the list into groups of 100 and combines the results into a single array

"""

from requests import Session
from requests.adapters import HTTPAdapter
from http import HTTPStatus
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import sys
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


class BaseNcmClient:
    def __init__(self,
                 log_events=True,
                 logger=None,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=None):
        """
        Constructor. Sets up and opens request session.
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
        self.log_events = log_events
        self.logger = logger
        self.session = Session()
        self.adapter = HTTPAdapter(
            max_retries=Retry(total=retries,
                              backoff_factor=retry_backoff_factor,
                              status_forcelist=retry_on,
                              redirect=3
                              )
        )
        self.base_url = base_url
        self.session.mount(self.base_url, self.adapter)
    
    def log(self, level, message):
        """
        Logs messages if self.logEvents is True.
        """
        if self.log_events:
            if self.logger:
                log_level = getattr(self.logger, level)
                log_level(message)
            else:
                print(f"{level}: {message}", file=sys.stderr) 

    def _return_handler(self, status_code, returntext, obj_type):
        """
        Prints returned HTTP request information if self.logEvents is True.
        """
        if str(status_code) == '200':
            return f'{obj_type} operation successful.'
        elif str(status_code) == '201':
            self.log('info', '{0} created Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '202':
            self.log('info', '{0} accepted Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '204':
            self.log('info', '{0} deleted Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '400':
            self.log('error', 'Bad Request')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '401':
            self.log('error', 'Unauthorized Access')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '404':
            self.log('error', 'Resource Not Found\n')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '500':
            self.log('error', 'HTTP 500 - Server Error\n')
            return f'ERROR: {status_code}: {returntext}'
        else:
            self.log('info', f'HTTP Status Code: {status_code} - {returntext}\n')


class NcmClientv2(BaseNcmClient):
    def __init__(self,
                 api_keys=None,
                 log_events=True,
                 logger=None,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=None):
        self.v2 = self # for backwards compatibility
        base_url = base_url or os.environ.get("CP_BASE_URL", "https://www.cradlepointecm.com/api/v2")
        super().__init__(log_events=log_events, logger=logger, retries=retries, retry_backoff_factor=retry_backoff_factor, retry_on=retry_on, base_url=base_url)
        if api_keys:
            if self.__validate_api_keys(api_keys):
                self.session.headers.update(api_keys)
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def __validate_api_keys(self, api_keys):
        """
        Checks NCM API Keys are a dictionary containing all necessary keys
        :param api_keys: Dictionary of API credentials. Optional.
        :type api_keys: dict
        :return: True if valid
        """
        if not isinstance(api_keys, dict):
            raise TypeError("API Keys must be passed as a dictionary")

        for key in ('X-CP-API-ID', 'X-CP-API-KEY', 'X-ECM-API-ID', 'X-ECM-API-KEY'):
            if not api_keys.get(key):
                raise KeyError(f"{key} missing. Please ensure all API Keys are present.")

        return True
    
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
                            self._return_handler(ncm.status_code,
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
                self._return_handler(ncm.status_code, ncm.json()['data'],
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
        
        self.__validate_api_keys(dict(self.session.headers)) 

        return params

    def __chunk_param(self, param):
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

        allowed_params = ['account', 'account__in', 'fields', 'id', 'id__in',
                          'name', 'name__in', 'expand', 'limit', 'offset']
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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

        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def put_group_configuration(self, group_id, config_json):
        """
        This method puts a group configuration for associated group id.
        :param group_id: ID of group to update
        :param config_json: JSON of the "configuration" field of the
          group config
        :return:
        """
        call_type = 'Configuration Manager'

        payload = config_json

        ncm = self.session.put(
            '{0}/groups/{1}/'.format(self.base_url, str(group_id)),
            data=json.dumps(payload))  # put group config with new values
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
        src_config = json.dumps(src_config).replace(', "wpapsk": "*"','').replace('"wpapsk": "*"', '').replace(', "password": "*"', '').replace('"password": "*"', '')

        """Get destination router Configuration Manager ID"""
        dst_config_man_id = \
            self.get_configuration_managers(router=dst_router_id)[0]['id']

        put_url = '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                           dst_config_man_id)

        ncm = self.session.patch(put_url, data=src_config)
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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

        allowed_params = ['id', 'id__in', 'router', 'router__in', 'limit', 'offset']
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
            result = self._return_handler(ncm.status_code, ncm.text,
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
                          'connection_state__in', 'fields', 'id', 'id__in',
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
                          'device_type__in', 'fields', 'group', 'group__in',
                          'id', 'id__in', 'ipv4_address', 'ipv4_address__in',
                          'mac', 'mac__in', 'name', 'name__in',
                          'reboot_required', 'reboot_required__in', 
                          'serial_number','state', 'state__in', 
                          'state_updated_at__lt', 'state_updated_at__gt', 
                          'updated_at__lt', 'updated_at__gt', 'expand', 
                          'order_by', 'limit', 'offset']
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        call_type = "Router"

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "group": 'https://www.cradlepointecm.com/api/v2/groups/{}/'.format(
                group_id)
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def remove_router_from_group(self, router_id=None, router_name=None):
        """
        This operation removes a router from its group.
        Either the ID or the name must be specified.
        :param router_id: ID of router to move.
        :param router_name: Name of router to move
        :return:
        """
        call_type = "Router"
        if not router_id and not router_name:
            return "ERROR: Either Router ID or Router Name must be specified."
        if not router_id:
            router_id = self.get_router_by_name(router_name)['id']

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {
            "group": None
        }

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        if ncm.status_code == 201 or ncm.status_code == 202:
            self.log('info', 'Router Modified Successfully')
            return None
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def delete_router_by_name(self, router_name):
        """
        This operation deletes a router by name.
        :param router_name: Name of router to delete
        :return:
        """
        return self.delete_router_by_id(
            self.get_router_by_name(router_name)['id'])

    def create_speed_test(self, net_device_ids: list, account_id=None,
                          host="netperf-west.bufferbloat.net",
                          max_test_concurrency=5, port=12865, size=None,
                          test_timeout=10, test_type="TCP Download", time=10):
        """
        This method creates a speed test using Netperf.

        Usage Example:
        n.create_speed_test([12345])

        :param account_id: Account in which to create the speed_test record.
        :param host: URL of Speedtest Server.
        :param max_test_concurrency: Number of maximum simultaneous tests to server (1-50).
        :param net_device_ids: List of net_device IDs (up to 10,000 net_device IDs per request).
        :param port: TCP port for test.
        :param size: Number of bytes to transfer.
        :param test_timeout: Test timeout in seconds.
        :param test_type: TCP Download, TCP Upload, TCP Latency
        :param time: Test time
        :return:
        """
        call_type = 'Speed Test'
        post_url = '{0}/speed_test/'.format(self.base_url)

        if account_id is None:
            account_id = self.get_accounts()[0]['id']

        post_data = {
            "account": f"https://www.cradlepointecm.com/api/v2/accounts/{account_id}/",
            "config": {
                "host": host,
                "max_test_concurrency": max_test_concurrency,
                "net_device_ids": net_device_ids,
                "port": port,
                "size": size,
                "test_timeout": test_timeout,
                "test_type": test_type,
                "time": time
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(post_data))
        if ncm.status_code == 201:
            return ncm.json()
        else:
            return ncm.text

    def create_speed_test_mdm(self, router_id, account_id=None,
                          host="netperf-west.bufferbloat.net",
                          max_test_concurrency=5, port=12865, size=None,
                          test_timeout=10, test_type="TCP Download", time=10):
        """
        This method creates a speed test using Netperf for all connected
        modems by specifying a router_id. This is helpful when the desired
        net_device_id(s) are not known

        Usage Example:
        n.create_speed_test_mdm(12345)

        :param account_id: Account in which to create the speed_test record.
        :param host: URL of Speedtest Server.
        :param max_test_concurrency: Number of maximum simultaneous tests to server (1-50).
        :param router_id: Router ID to test.
        :param port: TCP port for test.
        :param size: Number of bytes to transfer.
        :param test_timeout: Test timeout in seconds.
        :param test_type: TCP Download, TCP Upload, TCP Latency
        :param time: Test time
        :return:
        """

        net_devices = self.get_net_devices_for_router(router_id, connection_state='connected', is_asset=True)
        net_device_ids = [int(x["id"]) for x in net_devices]
        speed_test = self.create_speed_test(net_device_ids=net_device_ids,
                                            account_id=account_id,
                                            host=host,
                                            max_test_concurrency=max_test_concurrency,
                                            port=port,
                                            size=size,
                                            test_timeout=test_timeout,
                                            test_type=test_type,
                                            time=time)
        return speed_test

    def get_speed_test(self, speed_test_id, **kwargs):
        """
        This method gets the status/results of a created speed test.

        Usage Example:
        speed_test = n.create_speed_test([123456])
        n.get_speed_test(speed_test['id'])

        :param speed_test_id: ID of a speed_test record
        :return:
        """
        call_type = 'Speed Test'
        get_url = '{0}/speed_test/{1}/'.format(self.base_url, speed_test_id)

        return self.session.get(get_url).json()


    def set_lan_ip_address(self, router_id, lan_ip, netmask=None,
                           network_id=0):
        """
        This method sets the Primary LAN IP Address for a given router id.
        :param router_id: ID of router to update
        :param lan_ip: LAN IP Address. (e.g. 192.168.1.1)
        :param netmask: Subnet mask. (e.g. 255.255.255.0)
        :param network_id: The ID of the network to update.
          Numbering starts from 0. Defaults to Primary LAN.
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
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
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def set_admin_password(self, router_id: int, new_password: str):
        """
        This method sets the local admin password for a router.
        :param router_id: ID of router to update
        :param new_password: Cleartext password to assign
        :return:
        """
        call_type = 'Admin Password'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = {
            "configuration": [
                {
                    "system": {
                        "users": {
                            "0": {
                                "password": new_password
                            }
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_router_name(self, router_id: int, new_router_name: str):
        """
        This method sets the local admin password for a router.
        :param router_id: ID of router to update
        :param new_router_name: Name/System ID to set
        :return:
        """
        call_type = 'Router Name'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = {
            "configuration": [
                {
                    "system": {
                        "system_id": new_router_name
                    }
                },
                []
            ]
        }

        ncm = self.session.patch(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(config_man_id)),
            data=json.dumps(payload))  # Patch indie config with new values
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_router_description(self, router_id: int, new_router_description: str):
        """
        This method sets the local admin password for a router.
        :param router_id: ID of router to update
        :param new_router_description: Description string to set
        :return:
        """
        call_type = 'Description'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = {
            "configuration": [
                {
                    "system": {
                        "desc": new_router_description
                    }
                },
                []
            ]
        }

        ncm = self.session.patch(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(config_man_id)),
            data=json.dumps(payload))  # Patch indie config with new values
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_router_asset_id(self, router_id: int, new_router_asset_id: str):
        """
        This method sets the local admin password for a router.
        :param router_id: ID of router to update
        :param new_router_asset_id: Asset ID string to set
        :return:
        """
        call_type = 'Asset ID'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        payload = {
            "configuration": [
                {
                    "system": {
                        "asset_id": new_router_asset_id
                    }
                },
                []
            ]
        }

        ncm = self.session.patch(
            '{0}/configuration_managers/{1}/'.format(self.base_url,
                                                     str(config_man_id)),
            data=json.dumps(payload))  # Patch indie config with new values
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_ethernet_wan_ip(self, router_id: int, new_wan_ip: str,
                            new_netmask: str = None, new_gateway: str = None):
        """
        This method sets the Ethernet WAN IP Address for a given router id.
        :param router_id: ID of router to update
        :param new_wan_ip: IP Address to assign to Ethernet WAN
        :param new_netmask: Network Mask in dotted decimal notation (optional)
        :param new_gateway: IP of gateway (optional)
        :return:
        """
        call_type = 'Etheret WAN IP Address'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        ip_override = {
            "ip_address": new_wan_ip
        }

        if new_netmask:
            ip_override['netmask'] = new_netmask

        if new_gateway:
            ip_override['gateway'] = new_gateway

        payload = {
            "configuration": [
                {
                    "wan": {
                        "rules2": {
                            "0": {
                                "ip_override": ip_override
                            }
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def add_custom_apn(self, router_id: int, new_carrier: str, new_apn: str):
        """
        This method adds a new APN to the Advanced APN configuration
        :param router_id: ID of router to update
        :param new_carrier: Home Carrier / PLMN
        :param new_apn: APN
        :return:
        """
        call_type = 'Custom APN'

        response = self.session.get(
            '{0}/configuration_managers/?router.id={1}&fields=id,configuration'.format(
                self.base_url,
                str(router_id)))  # Get Configuration Managers ID
        response = json.loads(response.content.decode(
            "utf-8"))  # Decode the response and make it a dictionary
        config_man_id = response['data'][0][
            'id']  # get the Configuration Managers ID from response

        new_apn_id = 0
        try:
            if response['data'][0]['configuration'][0]['wan']:
                if response['data'][0]['configuration'][0]['wan']['custom_apns']:
                    new_apn_id = len(response['data'][0]['configuration'][0]['wan']['custom_apns'])
        except KeyError:
            pass

        payload = {
            "configuration": [
                {
                    "wan": {
                        "custom_apns": {
                            new_apn_id: {
                                "apn": new_apn,
                                "carrier": new_carrier
                            }
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
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def set_router_fields(self, router_id: int, name: str = None, description: str = None, asset_id: str = None, custom1: str = None, custom2: str = None):
        """
        This method sets multiple fields for a router.
        :param router_id: ID of router to update
        :param name: Name/System ID to set
        :param description: Description string to set
        :param asset_id: Asset ID string to set
        :param custom1: Custom1 field to set
        :param custom2: Custom2 field to set
        :return:
        """
        call_type = 'Router Fields'

        put_url = '{0}/routers/{1}/'.format(self.base_url, str(router_id))

        put_data = {}
        for k,v in (('name', name), ('description', description), ('asset_id', asset_id), ('custom1', custom1), ('custom2', custom2)):
            if v is not None:
                put_data[k] = v

        ncm = self.session.put(put_url, data=json.dumps(put_data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

class NcmClientv3(BaseNcmClient):
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __init__(self,
                 api_key=None,
                 log_events=False,
                 logger=None,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=None):
        """
        Constructor. Sets up and opens request session.
        :param api_key: API Bearer token (without the "Bearer" text).
          Optional, but must be set before calling functions.
        :type api_key: str
        :param log_events: if True, HTTP status info will be printed. False by default
        :type log_events: bool
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries.
          Optional.
        :param retry_on: types of errors on which automatic retry will occur.
          Optional.
        :param base_url: # base url for calls. Configurable for testing.
          Optional.
        """
        self.v3 = self # For backwards compatibility
        base_url = base_url or os.environ.get("CP_BASE_URL_V3", "https://api.cradlepointecm.com/api/v3")
        super().__init__(log_events, logger, retries, retry_backoff_factor, retry_on, base_url)
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        self.session.headers.update({
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json'
        })

    def __get_json(self, get_url, call_type, params=None):
        """
        Returns full paginated results
        """
        results = []

        if params is not None and "limit" in params:
            limit = params['limit']
            if limit == 0:
                limit = 1000000
            if params['limit'] > 50 or params['limit'] == 0:
                params['page[size]'] = 50
            else:
                params['page[size]'] = params['limit']
        else:
            limit = 50

        url = get_url

        while url and (len(results) < limit):
            ncm = self.session.get(url, params=params)
            if not (200 <= ncm.status_code < 300):
                return self._return_handler(ncm.status_code, ncm.json(), call_type)
            data = ncm.json()['data']
            if isinstance(data, list):
                self._return_handler(ncm.status_code, data, call_type)
                for d in data:
                    results.append(d)
            else:
                results.append(data)
            if "links" in ncm.json():
                url = ncm.json()['links']['next']
            else:
                url = None

        if params is not None and "filter[fields]" in params.keys():
            data = []
            fields = params['filter[fields]'].split(",")
            for result in results:
                items = {}
                for k, v in result['attributes'].items():
                    if k in fields:
                        items[k] = v
                data.append(items)
            return data

        return results


    def __parse_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """
        if 'search' in kwargs:
            return self.__parse_search_kwargs(kwargs, allowed_params)

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        params = {}

        for key, val in kwargs.items():
            if "search" in key or "filter" in key or "sort" in key or "limit" in key:
                params[key] = val

            elif "__" in key:
                split_key = key.split("__")
                params[f'filter[{split_key[0]}][{split_key[1]}]'] = val
            else:
                params[f'filter[{key}]'] = val

        return params

    def __parse_search_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "search" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        params = {}

        for key, val in kwargs.items():
            if "filter" in key or "sort" in key or "limit" in key:
                params[key] = val
            elif "fields" in key:
                params[f'filter[{key}]'] = val
            else:
                if "search" not in key:
                    params[f'search[{key}]'] = val

        return params

    def __parse_put_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        return kwargs

    def set_api_key(self, api_key):
        """
        Sets NCM API Keys for session.
        :param api_key: API Bearer token (without the "Bearer" prefix).
        :type api_key: str
        """
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        return

    def get_users(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Users'
        get_url = f'{self.base_url}/beta/users'

        allowed_params = ['email',
                          'email__not',
                          'first_name',
                          'first_name__ne',
                          'id',
                          'is_active__ne',
                          'last_login',
                          'last_login__lt',
                          'last_login__lte',
                          'last_login__gt',
                          'last_login__gte',
                          'last_login__ne',
                          'last_name',
                          'last_name__ne',
                          'pending_email',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_user(self, email, first_name, last_name, **kwargs):
        """
        Creates a user.
        :param email: Email address
        :type email: str
        :param first_name: First name
        :type first_name: str
        :param last_name: Last name
        :type last_name: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User creation result.
        """
        call_type = 'User'
        post_url = f'{self.base_url}/beta/users'

        allowed_params = ['is_active',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)
        params['email'] = email
        params['first_name'] = first_name
        params['last_name'] = last_name

        """GET TENANT ID"""
        t = self.get_subscriptions(limit=1)

        data = {
            "data": {
                "type": "users",
                "attributes": params,
                "relationships": {
                    "tenant": {
                        "data": [t[0]['relationships']['tenants']['data']]
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def update_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User update result.
        """
        call_type = 'Users'

        user = self.get_users(email=email)[0]
        user.pop('links')

        put_url = f'{self.base_url}/beta/users/{user["id"]}'

        allowed_params = ['first_name',
                          'last_name',
                          'is_active',
                          'user_id',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            user['attributes'][k] = v

        user = {"data": user}

        ncm = self.session.put(put_url, data=json.dumps(user))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: None unless error.
        """
        call_type = 'Users'

        user = self.get_users(email=email)[0]
        user.pop('links')

        delete_url = f'{self.base_url}/beta/users/{user["id"]}'

        ncm = self.session.delete(delete_url)
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_asset_endpoints(self, **kwargs):
        """
        Returns assets with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of asset endpoints (routers) with details.
        """
        call_type = 'Asset Endpoints'
        get_url = f'{self.base_url}/asset_endpoints'

        allowed_params = ['id',
                          'hardware_series',
                          'hardware_series_key',
                          'mac_address',
                          'serial_number',
                          'fields',
                          'limit',
                          'sort']
        
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_subscriptions(self, **kwargs):
        """
        Returns subscriptions with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of subscriptions with details.
        """
        call_type = 'Subscriptions'
        get_url = f'{self.base_url}/subscriptions'

        allowed_params = ['end_time',
                          'end_time__lt',
                          'end_time__lte',
                          'end_time__gt',
                          'end_time__gte',
                          'end_time__ne',
                          'id',
                          'name',
                          'quantity',
                          'start_time',
                          'start_time__lt',
                          'start_time__lte',
                          'start_time__gt',
                          'start_time__gte',
                          'start_time__ne',
                          'tenant',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)
    
    def regrade(self, subscription_id, mac_or_serial_number, action="UPGRADE"):
        """ 
        Applies a subscription to an asset.
        :param subscription_id: ID of the subscription to apply. See https://developer.cradlepoint.com/ for list of subscriptions.
        :param mac_or_serial_number: MAC address or serial number of the asset to apply the subscription to. Can also be a list.
        :param action: Action to take. Default is "UPGRADE". Can also be "DOWNGRADE".
        """

        call_type = 'Subscription'
        post_url = f'{self.base_url}/asset_endpoints/regrades'

        payload = {
            "atomic:operations": []
        }
        mac_or_serial_number = mac_or_serial_number if isinstance(mac_or_serial_number, list) else [mac_or_serial_number]
        for smac in mac_or_serial_number:
            data = {
                "op": "add",
                "data": {
                    "type": "regrades",
                    "attributes": {
                        "action": action,
                        "subscription_type": subscription_id
                    }
                }
            }
            if len(smac) == 17:
                data['data']['attributes']['mac_address'] = smac.replace(':','')
            elif len(smac) == 12:
                data['data']['attributes']['mac_address'] = smac
            else:
                data['data']['attributes']['serial_number'] = smac
            payload["atomic:operations"].append(data)

        ncm = self.session.post(post_url, json=payload)
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def get_regrades(self, **kwargs):
        """
        Returns regrade jobs with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of regrades with details.
        """
        call_type = 'Subscription'
        get_url = f'{self.base_url}/asset_endpoints/regrades'

        allowed_params = ["id", 
                    "action_id", 
                    "mac_address", 
                    "created_at", 
                    "action", 
                    "subcription_type", 
                    "status", 
                    "error_code"]

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_networks(self, **kwargs):
        """
        Returns information about your private cellular networks.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of PCNs with details.
        """
        call_type = 'Private Cellular Networks'
        get_url = f'{self.base_url}/beta/private_cellular_networks'

        allowed_params = ['core_ip',
                          'created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'ha_enabled',
                          'id',
                          'mobility_gateways',
                          'mobility_gateway_virtual_ip',
                          'name',
                          'state',
                          'status',
                          'tac',
                          'type',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'fields',
                          'limit',
                          'sort']
        
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_network(self, network_id, **kwargs):
        """
        Returns information about a private cellular network.
        :param network_id: ID of the private_cellular_networks record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual PCN network with details.
        """
        call_type = 'Private Cellular Networks'
        get_url = f'{self.base_url}/beta/private_cellular_networks/{network_id}'

        allowed_params = ['name',
                          'segw_ip',
                          'ha_enabled',
                          'mobility_gateway_virtual_ip',
                          'state',
                          'status',
                          'tac',
                          'created_at',
                          'updated_at',
                          'fields']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def update_private_cellular_network(self, id=None, name=None, **kwargs):
        """
        Make changes to a private cellular network.
        :param id: PCN network ID. Specify either this or name.
        :type id: str
        :param name: PCN network name
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: PCN update result.
        """
        call_type = 'Private Cellular Network'

        if not id and not name:
            return "ERROR: no network specified. Must specify either network_id or network_name"

        if id:
            net = self.get_private_cellular_networks(id=id)[0]
        elif name:
            net = self.get_private_cellular_networks(name=name)[0]

        if name:
            kwargs['name'] = name

        net.pop('links')

        put_url = f'{self.base_url}/beta/private_cellular_networks/{net["id"]}'

        allowed_params = ['core_ip',
                          'ha_enabled',
                          'id',
                          'mobility_gateways',
                          'mobility_gateway_virtual_ip',
                          'name',
                          'state',
                          'status',
                          'tac',
                          'type']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            net['attributes'][k] = v

        data = {"data": net}

        ncm = self.session.put(put_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_private_cellular_network(self, name, core_ip, ha_enabled=False, mobility_gateway_virtual_ip=None, mobility_gateways=None):
        """
        Make changes to a private cellular network.
        :param name: Name of the networks.
        :type name: str
        :param core_ip: IP address to reach core network.
        :type core_ip: str
        :param ha_enabled: High availability (HA) of network.
        :type ha_enabled: bool
        :param mobility_gateway_virtual_ip: Virtual IP address to reach core when HA is enabled. Nullable.
        :type mobility_gateway_virtual_ip: str
        :param mobility_gateways: Comma separated list of private_cellular_cores IDs to add as mobility gateways. Nullable.
        :type mobility_gateways: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Create PCN result..
        """
        call_type = 'Private Cellular Network'

        post_url = f'{self.base_url}/beta/private_cellular_networks'

        data = {
            "data": {
                "type": "private_cellular_networks",
                "attributes": {
                    "name": name,
                    "core_ip": core_ip,
                    "ha_enabled": ha_enabled,
                    "mobility_gateway_virtual_ip": mobility_gateway_virtual_ip
                }
            }
        }

        if mobility_gateways:
            relationships = {
                "mobility_gateways": {
                    "data": []
                }
            }
            gateways = mobility_gateways.split(",")

            for gateway in gateways:
                relationships['mobility_gateways']['data'].append({"type": "private_cellular_cores", "id": gateway})

            data['data']['relationships'] = relationships

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_private_cellular_network(self, id):
        """
        Returns information about a private cellular network.
        :param id: ID of the private_cellular_networks record
        :type id: str
        :return: None unless error.
        """
        # TODO support deletion by network name
        call_type = 'Private Cellular Network'
        delete_url = f'{self.base_url}/beta/private_cellular_networks/{id}'

        ncm = self.session.delete(delete_url)
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_private_cellular_cores(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Mobility Gateways with details.
        """
        call_type = 'Private Cellular Cores'
        get_url = f'{self.base_url}/beta/private_cellular_cores'

        allowed_params = ['created_at',
                          'id',
                          'management_ip',
                          'network',
                          'router',
                          'status',
                          'type',
                          'updated_at',
                          'url',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_core(self, core_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param core_id: ID of the private_cellular_cores record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Mobility Gateway with details.
        """
        call_type = 'Private Cellular Core'
        get_url = f'{self.base_url}/beta/private_cellular_cores/{core_id}'

        allowed_params = ['created_at',
                          'id',
                          'management_ip',
                          'network',
                          'router',
                          'status',
                          'type',
                          'updated_at',
                          'url',
                          'fields',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radios(self, **kwargs):
        """
        Returns information about a private cellular radio.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Cellular APs with details.
        """
        call_type = 'Private Cellular Radios'
        get_url = f'{self.base_url}/beta/private_cellular_radios'

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radio(self, id, **kwargs):
        """
        Returns information about a private cellular radio.
        :param id: ID of the private_cellular_radios record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Cellular AP with details.
        """
        call_type = 'Private Cellular Radios'
        get_url = f'{self.base_url}/beta/private_cellular_radios/{id}'

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def update_private_cellular_radio(self, id=None, name=None, **kwargs):
        """
        Updates a Cellular AP's data.
        :param id: ID of the private_cellular_radio record. Must specify this or name.
        :type id: str
        :param name: Name of the Cellular AP. Must specify this or id.
        type id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update Cellular AP results.
        """
        call_type = 'Private Cellular Radio'

        if id:
            radio = self.get_private_cellular_radios(id=id)[0]
        elif name:
            radio = self.get_private_cellular_radios(name=name)[0]
        else:
            return "ERROR: Must specify either ID or name"

        if name:
            kwargs['name'] = name

        put_url = f'{self.base_url}/beta/private_cellular_radios/{radio["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            radio['data']['relationships'] = relationships

        if "location" in kwargs.keys():
            location = {
                "data": {
                    "type": "private_cellular_radio_groups",
                    "id": kwargs['location']
                }
            }
            kwargs.pop("location")
            radio['data']['location'] = location

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            radio['attributes'][k] = v

        radio = {"data": radio}

        ncm = self.session.put(put_url, data=json.dumps(radio))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def get_private_cellular_radio_groups(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Cellular AP Groups with details.
        """
        call_type = 'Private Cellular Radio Groups'
        get_url = f'{self.base_url}/beta/private_cellular_radio_groups'

        allowed_params = ['created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'description',
                          'id',
                          'name',
                          'network',
                          'type',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radio_group(self, group_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param group_id: ID of the private_cellular_radio_groups record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Cellular AP Group with details.
        """
        call_type = 'Private Cellular Radio Group'
        get_url = f'{self.base_url}/beta/private_cellular_radio_groups/{group_id}'

        allowed_params = ['created_at',
                          'description',
                          'id',
                          'name',
                          'network',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def update_private_cellular_radio_group(self, id=None, name=None, **kwargs):
        """
        Updates a Radio Group.
        :param id: ID of the private_cellular_radio_groups record. Must specify this or name.
        :type id: str
        :param name: Name of the Radio Group. Must specify this or id.
        type name: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update Cellular AP Group results.
        """
        call_type = 'Private Cellular Radio Group'

        if id:
            group = self.get_private_cellular_radio_groups(id=id)[0]
        elif name:
            group = self.get_private_cellular_radio_groups(name=name)[0]
        else:
            return "ERROR: Must specify either ID or name"

        if name:
            kwargs['name'] = name

        put_url = f'{self.base_url}/beta/private_cellular_sims/{group["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            group['data']['relationships'] = relationships

        allowed_params = ['name',
                          'description']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            group['attributes'][k] = v

        group = {"data": group}

        ncm = self.session.put(put_url, data=json.dumps(group))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_private_cellular_radio_group(self, name, description, network=None):
        """
        Creates a Radio Group.
        :param name: Name of the Radio Group.
        type name: str
        :param description: Description of the Radio Group.
        :type description: str
        param network: ID of the private_cellular_network to belong to. Optional.
        :type network: str
        :return: Create Private Cellular Radio Group results.
        """
        call_type = 'Private Cellular Radio Group'

        post_url = f'{self.base_url}/beta/private_cellular_radio_groups'

        group = {
            "data": {
                "type": "private_cellular_radio_groups",
                "attributes": {
                    "name": name,
                    "description": description
                }
            }
        }

        if network:
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": network
                    }
                }
            }

            group['data']['relationships'] = relationships

        ncm = self.session.post(post_url, data=json.dumps(group))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_private_cellular_radio_group(self, id):
        """
        Deletes a private_cellular_radio_group record.
        :param id: ID of the private_cellular_radio_group record
        :type id: str
        :return: None unless error.
        """
        #TODO support deletion by group name
        call_type = 'Private Cellular Radio Group'
        delete_url = f'{self.base_url}/beta/private_cellular_radio_group/{id}'

        ncm = self.session.delete(delete_url)
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_private_cellular_sims(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of PCN SIMs with details.
        """
        call_type = 'Private Cellular SIMs'
        get_url = f'{self.base_url}/beta/private_cellular_sims'

        allowed_params = ['created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'iccid',
                          'id',
                          'imsi',
                          'last_contact_at',
                          'last_contact_at__lt',
                          'last_contact_at__lte',
                          'last_contact_at__gt',
                          'last_contact_at__gte',
                          'last_contact_at__ne',
                          'name',
                          'network',
                          'state',
                          'state_updated_at',
                          'state_updated_at__lt',
                          'state_updated_at__lte',
                          'state_updated_at__gt',
                          'state_updated_at__gte',
                          'state_updated_at__ne',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_sim(self, id, **kwargs):
        """
        Returns information about a private cellular core.
        :param sim_id: ID of the private_cellular_sims record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual PCN SIM with details.
        """
        call_type = 'Private Cellular SIMs'
        get_url = f'{self.base_url}/beta/private_cellular_sims/{id}'

        allowed_params = ['created_at',
                          'iccid',
                          'id',
                          'imsi',
                          'last_contact_at',
                          'name',
                          'network',
                          'state',
                          'state_updated_at',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def update_private_cellular_sim(self, id=None, iccid=None, imsi=None, **kwargs):
        """
        Updates a SIM's data.
        :param id: ID of the private_cellular_sim record. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param iccid: ICCID. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param imsi: IMSI. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update PCN SIM results.
        """
        call_type = 'Private Cellular SIM'

        if id:
            sim = self.get_private_cellular_sims(id=id)[0]
        elif iccid:
            sim = self.get_private_cellular_sims(iccid=iccid)[0]
        elif imsi:
            sim = self.get_private_cellular_sims(imsi=imsi)[0]
        else:
            return "ERROR: Must specify either ID, ICCID, or IMSI"

        put_url = f'{self.base_url}/beta/private_cellular_sims/{sim["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            sim['data']['relationships'] = relationships

        allowed_params = ['name',
                          'state']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            sim['attributes'][k] = v

        sim = {"data": sim}

        ncm = self.session.put(put_url, data=json.dumps(sim))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def get_private_cellular_radio_statuses(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Cellular radio status for all cellular radios.
        """
        call_type = 'Private Cellular Radio Statuses'
        get_url = f'{self.base_url}/beta/private_cellular_radio_statuses'

        allowed_params = ['admin_state',
                          'boot_time',
                          'cbrs_sas_status',
                          'cell',
                          'connected_ues',
                          'ethernet_status',
                          'id',
                          'ipsec_status',
                          'ipv4_address',
                          'last_update_time',
                          'online_status',
                          'operational_status',
                          'operating_tx_power',
                          's1_status',
                          'time_synchronization',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radio_status(self, status_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param status_id: ID of the private_cellular_radio_statuses resource
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Cellular radio status for an individual radio.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/private_cellular_radio_statuses/{status_id}'

        allowed_params = ['admin_state',
                          'boot_time',
                          'cbrs_sas_status',
                          'cell',
                          'connected_ues',
                          'ethernet_status',
                          'id',
                          'ipsec_status',
                          'ipv4_address',
                          'last_update_time',
                          'online_status',
                          'operational_status',
                          'operating_tx_power',
                          's1_status',
                          'time_synchronization',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)


    def get_public_sim_mgmt_assets(self, **kwargs):
        """
        Returns information about SIM asset resources in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: SIM asset resources.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/public_sim_mgmt_assets'

        allowed_params = ['assigned_imei',
                          'carrier',
                          'detected_imei',
                          'device_status',
                          'iccid',
                          'is_licensed'
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_public_sim_mgmt_rate_plans(self, **kwargs):
        """
        Returns information about rate plan resources associated with the SIM assets in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Rate plans for SIM assets.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/public_sim_mgmt_assets'

        allowed_params = ['carrier',
                          'name',
                          'status',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)


    def get_exchange_sites(self, **kwargs):
        """
        Returns exchange sites.
        :param kwargs: A set of zero or more allowed parameters
        in the allowed_params list.
        :return: A list of exchange sites or a single site if site_id is provided.
        """
        call_type = 'Exchange Sites'
        get_url = f'{self.base_url}/beta/exchange_sites'

        if 'site_id' in kwargs:
            get_url += f'/{kwargs["site_id"]}'
            response = self.__get_json(get_url, call_type)
            return response

        allowed_params = ['exchange_network',
                        'name',
                        'fields',
                        'limit',
                        'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_exchange_site(self, name, exchange_network_id, router_id, local_domain=None, primary_dns=None, secondary_dns=None, lan_as_dns=False):
        """
        Creates an exchange site.
        :param name: Name of the exchange site.
        :type name: str
        :param primary_dns: Primary DNS of the exchange site.
        :type primary_dns: str
        :param secondary_dns: Secondary DNS of the exchange site.
        :type secondary_dns: str
        :param lan_as_dns: Whether LAN is used as DNS.
        :type lan_as_dns: bool
        :param local_domain: Local domain of the exchange site.
        :type local_domain: str
        :param exchange_network_id: ID of the exchange network.
        :type exchange_network_id: str
        :param router_id: ID of the endpoint.
        :type router_id: str
        :return: The response from the POST request.
        """
        call_type = 'Create Exchange Site'

        post_url = f'{self.base_url}/beta/exchange_sites'

        data = {
            "data": {
                "type": "exchange_user_managed_sites",
                "attributes": {
                    "name": name,
                    "primary_dns": primary_dns,
                    "secondary_dns": secondary_dns,
                    "lan_as_dns": lan_as_dns,
                    "local_domain": local_domain
                },
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "id": exchange_network_id,
                            "type": "exchange_networks"
                        }
                    },
                    "endpoints": {
                        "data": [
                            {
                                "id": router_id,
                                "type": "endpoints"
                            }
                        ]
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result

    def update_exchange_site(self, site_id, **kwargs):
        """
        Updates an exchange site.
        :param site_id: ID of the exchange site to update.
        :type site_id: str
        :param kwargs: Keyword arguments for the attributes and relationships of the exchange site.
        :return: The response from the PUT request.
        """
        call_type = 'Update Exchange Site'
        put_url = f'{self.base_url}/beta/exchange_sites/{site_id}'

        allowed_params = ['name', 'primary_dns', 'secondary_dns', 'lan_as_dns', 'local_domain']

        current_site = self.get_exchange_sites(site_id=site_id)[0]
        exchange_network_id = current_site['relationships']['exchange_network']['data']['id']
        router_id = current_site['relationships']['endpoints']['data'][0]['id']
        attributes = current_site['attributes']

        for key, value in kwargs.items():
            if key in allowed_params:
                attributes['key'] = value

        ncm = self.session.put(put_url, data=json.dumps({
            "data": {
                "type": "exchange_user_managed_sites",
                "id": site_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "type": "exchange_networks",
                            "id": exchange_network_id
                        }
                    },
                    "endpoints": {
                        "data": [{
                            "type": "routers",
                            "id": router_id
                        }]
                    }
                }
            }
        }))

        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_exchange_site(self, site_id):
        """
        Deletes an exchange site.
        :param site_id: ID of the exchange site to delete.
        :type site_id: str
        :return: The response from the DELETE request.
        """
        call_type = 'Delete Exchange Site'
        delete_url = f'{self.base_url}/beta/exchange_sites{site_id}'

        ncm = self.session.delete(delete_url)
        result = self._return_handler(ncm.status_code, ncm, call_type)
        return result

    def get_exchange_resources(self, exchange_network=None, exchange_site=None, **kwargs):
        """
        Returns exchange sites.
        :param kwargs: A set of zero or more allowed parameters
        in the allowed_params list.
        :return: A list of exchange sites or a single site if site_id is provided.
        """
        call_type = 'Exchange Resources'
        get_url = f'{self.base_url}/beta/exchange_resources'

        params = {}

        allowed_params = ['exchange_network',
                          'name',
                          'id',
                          'fields',
                          'limit',
                          'sort']

        if kwargs:
            params = self.__parse_kwargs(kwargs, allowed_params)

        if exchange_site:
            params['filter[exchange_site]'] = exchange_site
        elif exchange_network:
            params['filter[exchange_network]'] = exchange_network

        response = self.__get_json(get_url, call_type, params=params)
        return response

    def create_exchange_resource(self, site_id, resource_name, resource_type, **kwargs):
        """
        Creates an exchange site.
        :param site_id: NCX Site ID to add the resource to.
        :type site_id: str
        :param resource_name: Name for the new resource
        :type resource_type: str
        :param resource_type: exchange_fqdn_resources, exchange_wildcard_fqdn_resources, or exchange_ipsubnet_resources
        :type resource_type: str

        :return: The response from the POST request.
        """
        call_type = 'Create Exchange Site Resource'

        post_url = f'{self.base_url}/beta/exchange_resources'
        allowed_params = ['name',
                          'protocols',
                          'tags',
                          'domain',
                          'ip',
                          'static_prime_ip',
                          'port_ranges',
                          'fields',
                          'limit',
                          'sort']

        attributes = {key: value for key, value in kwargs.items() if key in allowed_params}
        attributes['name'] = resource_name

        data = {
            "data": {
                "type": resource_type,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "id": site_id,
                            "type": "exchange_sites"
                        }
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result

    def update_exchange_resource(self, resource_id, exchange_network=None, exchange_site=None, **kwargs):
        """
        Updates an exchange site.
        :param resource_id: ID of the exchange resource to update.
        :type resource_id: str
        :param kwargs: Keyword arguments for the attributes and relationships of the exchange site.
        :return: The response from the PUT request.
        """
        call_type = 'Update Exchange Site'
        put_url = f'{self.base_url}/beta/exchange_resources/{resource_id}'

        allowed_params = ['name',
                          'protocols',
                          'tags',
                          'domain',
                          'ip',
                          'static_prime_ip',
                          'port_ranges']

        if exchange_site:
            current_resource = self.get_exchange_resources(exchange_site=exchange_site, id=resource_id)[0]
        elif exchange_network:
            current_resource = self.get_exchange_resources(exchange_network=exchange_network, id=resource_id)[0]

        exchange_site_id = current_resource['relationships']['exchange_site']['data']['id']
        attributes = current_resource['attributes']

        for key, value in kwargs.items():
            if key in allowed_params:
                attributes['key'] = value

        ncm = self.session.put(put_url, data=json.dumps({
            "data": {
                "type": current_resource['type'],
                "id": resource_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "type": "exchange_sites",
                            "id": exchange_site_id
                        }
                    }
                }
            }
        }))

        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_exchange_resource(self, resource_id):
        """
        Deletes an exchange resource.
        :param resource_id: ID of the exchange resource to delete.
        :type resource_id: str
        :return: The response from the DELETE request.
        """
        call_type = 'Delete Exchange Site'
        delete_url = f'{self.base_url}/beta/exchange_resources{resource_id}'

        ncm = self.session.delete(delete_url)
        result = self._return_handler(ncm.status_code, ncm, call_type)
        return result

'''
    def get_group_modem_upgrade_jobs(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['id',
                          'group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'batch_size',
                          'created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'available_version',
                          'modem_count',
                          'success_count',
                          'failed_count',
                          'statuscarrier_name',
                          'module_name',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_job(self, job_id, **kwargs):
        """
        Returns users with details.
        :param job_id: The ID of the job
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs/{job_id}'

        allowed_params = ['id',
                          'group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'batch_size',
                          'created_at',
                          'updated_at',
                          'available_version',
                          'modem_count',
                          'success_count',
                          'failed_count',
                          'statuscarrier_name',
                          'module_name',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_summary(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['group_id',
                          'module_id',
                          'module_name',
                          'upgradable_modems',
                          'up_to_date_modems',
                          'summary_data',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_device_summary(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'router_name',
                          'net_device_name',
                          'current_version',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)
'''

class NcmClientv2v3:

    def __init__(self, 
              api_keys=None,
              api_key=None,
              log_events=True,
              logger=None,
              retries=5,
              retry_backoff_factor=2,
              retry_on=None,
              base_url=None,
              base_url_v3=None):
        """
        :param api_keys: Dictionary of API credentials (apiv2).
            Optional, but must be set before calling functions.
        :type api_keys: dict
        :param api_key: API key for apiv3.
            Optional, but must be set before calling functions.
        :type api_key: str
        """
        api_keys = api_keys or {}
        apiv3_key = api_keys.pop('token', None) or api_key
        self.v2 = None
        self.v3 = None
        if api_keys:
            self.v2 = NcmClientv2(api_keys=api_keys, 
                                  log_events=log_events,
                                  logger=logger,
                                  retries=retries, 
                                  retry_backoff_factor=retry_backoff_factor, 
                                  retry_on=retry_on, 
                                  base_url=base_url)
        if apiv3_key:
            base_url = base_url_v3 if api_keys else base_url
            self.v3 = NcmClientv3(api_key=apiv3_key, 
                                  log_events=log_events, 
                                  logger=logger,
                                  retries=retries, 
                                  retry_backoff_factor=retry_backoff_factor, 
                                  retry_on=retry_on, 
                                  base_url=base_url)
        
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            # Prioritize v3 over v2
            if self.v3 and hasattr(self.v3, name):
                return getattr(self.v3, name)
            if self.v2 and hasattr(self.v2, name):
                return getattr(self.v2, name)
            raise


class NcmClient:
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __new__(cls, api_keys=None, api_key=None, **kwargs):
        api_keys = api_keys or {}
        apiv3_key = api_keys.pop('token', None) or api_key
        v2 = bool(api_keys)
        v3 = bool(apiv3_key)
        if v2 and v3:
            return NcmClientv2v3(api_keys=api_keys, api_key=apiv3_key, **kwargs)
        if v2 or not (v2 or v3):
            return NcmClientv2(api_keys=api_keys, **kwargs)
        else:
            return NcmClientv3(api_key=apiv3_key, **kwargs)
