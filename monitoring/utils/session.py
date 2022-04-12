"""
Session class handy for wrapping calls to the server.

Some ways this class helps you:

1. Simplifies construction of HTTP calls (headers, params, order_by)
2. Transparently retries on certain types of errors. This is particularly
helpful for server timeouts and dropped connections.
3. Automatically pages by converting the returned records into a
generator/stream and transparently fetching the "next" url for you.

"""

from urllib3.util.retry import Retry
from requests import Session
from requests.adapters import HTTPAdapter
from http import HTTPStatus
import os


class APISession(object):
    """
    Wrapper for API session and GET requests.
    """

    def __init__(
        self,
        logger=None,
        ecm_api_id=None,
        ecm_api_key=None,
        cp_api_id=None,
        cp_api_key=None,
        retries=5,
        retry_backoff_factor=2,
        retry_on=[  #
            HTTPStatus.REQUEST_TIMEOUT,
            HTTPStatus.GATEWAY_TIMEOUT,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ],
        base_url=os.environ.get("CP_BASE_URL", "https://www.cradlepointecm.com/api/v2"),
    ):
        """
        Constructor.  Sets up and opens request session.

        :param logger: a logger to write progress/error messages to. Required.
        :param ecm_api_id: API credentials. Required.
        :param ecm_api_key: API credentials. Required.
        :param cp_api_key: API credentials. Required.
        :param cp_api_id: API credentials. Required.
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries. Optional.
        :param retry_on: types of errors on which automatic retry will occur. Optional.
        :param base_url: # base url for calls. Configurable for testing. Optional.
        """
        self.base_url = base_url
        self.session = Session()
        self.adapter = HTTPAdapter(
            max_retries=Retry(
                total=retries,
                backoff_factor=retry_backoff_factor,
                status_forcelist=retry_on,
                redirect=3,
            )
        )
        self.session.mount(base_url, self.adapter)
        self.session.headers.update(
            {
                "X-ECM-API-ID": ecm_api_id,
                "X-ECM-API-KEY": ecm_api_key,
                "X-CP-API-ID": cp_api_id,
                "X-CP-API-KEY": cp_api_key,
            }
        )
        self.logger = logger
        self.logger.info("Opening session")

    def __enter__(self):
        """
        Support for using this class as a context manager.
        """
        return self

    def __exit__(self, *args):
        """
        Support for using this class as a context manager.
        """
        self.close()

    def close(self):
        """
        Close session opened in constructor.
        """
        self.session.close()
        self.logger.info("Closing session")

    def _get_iterator(self, response, next):
        """
        Generator function returned by get().
        """
        if isinstance(response, list):
            while response:
                yield response.pop(0)
            if next:
                for row in self.get(url=next):
                    yield row
        else:
            yield response

    def get(self, endpoint=None, url=None, batchsize=25, order_by=[], filter={}):
        """
        Execute a "GET" against the given endpoint.

        :param endpoint: endpoint to call. Either this or url needs to be specified.
        :param url: full url to call.
        :param batchsize: page size for calls to server. Optional.
        :param order_by: sort column(s)
        :filter filter fields as a map where (key,value) corresponds to
        key=value on the query string.

        :return: a generator yielding the results.  Transparently
        pages and retries, as necessary.
        """
        if not url:
            url = f"{self.base_url}/{endpoint}/"

        params = filter.copy()
        params["limit"] = batchsize
        if order_by:
            params["order_by"] = ",".join(order_by)
        response = self.session.get(url, params=params)
        self.logger.info(f"Getting from URL {response.url}")
        if response.ok:
            response = response.json()
            next = response.get("meta", {}).get("next")
            response = response.get("data", response)
            return self._get_iterator(response, next)
        else:
            raise Exception(
                f"Error executing GET {url}: "
                f"{response.status_code}: {response.content}"
            )
