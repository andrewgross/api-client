import requests
import logging
import sys
import json

from time import sleep

logger = logging.getLogger(__name__)


class Client(object):
    """
    A Client for interacting with a remote API
    """
    def __init__(self,
                 account_id=None,
                 api_key=None,
                 proxy=None,
                 retries=3,
                 retry_delay=0.5,
                 timeout=1.000,
                 debug=False):
        """
        Create a REST(ish?) API client
        Required Parameters: account_id, api_key
        Optional Parameters: proxy, retries, retry_delay, timeout, debug
        """
        # Get Account Credentials

        if not account_id or not api_key:
            raise CredentialException("""
The Client could not find your account credentials.
Pass them into the Client like this:

    client = pyrelic.Client(account='12345',
                            apikey='1234567890abcdef123456789')

                """)

        self.account_id = account_id
        self.api_key = api_key
        self.headers = {'x-api-key': api_key}
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self.debug = debug
        if self.debug is True:
            self.config = {'verbose': sys.stderr}
        else:
            self.config = {}

    def _make_request(self, request, uri, **kwargs):
        attempt = 1
        response = None
        while attempt <= self.retries:
            try:
                response = request(uri,
                                   config=self.config,
                                   headers=self.headers,
                                   proxies=self.proxy,
                                   **kwargs)
            except (requests.ConnectionError, requests.HTTPError) as ce:
                logger.error('Error connecting to Remote API: {}'.format(ce))
                sleep(self.retry_delay)
                attempt += 1
            else:
                break
        if not response and attempt > 1:
            raise ApiException("""
                               Unable to connect to the remote API after {} attempts
                               """.format(attempt))
        if not response:
            raise ApiException('No response received from remote API')
        if not str(response.status_code).startswith('2'):
            self._handle_api_error(response.status_code)
        return self._parse_xml(response.text)

    def _parse_json(self, response):
        parsed_response = json.decode(response)
        return parsed_response

    def _handle_api_error(self, status_code, error_message):
        error_code_mappings = {
            403: InvalidApiKeyException(error_message),
            404: UnknownApplicationException(error_message),
            422: InvalidParameterException(error_message),
        }

        if status_code in error_code_mappings.keys():
            raise error_code_mappings[status_code]
        else:
            raise ApiException(error_message)

    def _make_get_request(self, uri, parameters=None, timeout=None):
        """
        Given a request add in the required parameters and return the
        parsed XML object.
        """
        if not timeout:
            timeout = self.timeout
        return self._make_request(requests.get,
                                  uri,
                                  params=parameters,
                                  timeout=timeout)

    def _make_post_request(self, uri, payload, timeout=None):
        """
        Given a request add in the required parameters and return the
        parsed object.
        """
        if not timeout:
            timeout = self.timeout
        return self._make_request(requests.post,
                                  uri,
                                  payload,
                                  timeout=timeout)


class ApiException(Exception):
    def __init__(self, message):
        super(ApiException, self).__init__()
        print message


class InvalidApiKeyException(ApiException):
    def __init__(self, message):
        super(InvalidApiKeyException, self).__init__(message)
        pass


class CredentialException(ApiException):
    def __init__(self, message):
        super(CredentialException, self).__init__(message)
        pass


class InvalidParameterException(ApiException):
    def __init__(self, message):
        super(InvalidParameterException, self).__init__(message)
        pass


class ApiRateLimitException(ApiException):
    def __init__(self, message):
        super(ApiRateLimitException, self).__init__(message)
        self.timeout = message


class UnknownApplicationException(ApiException):
    def __init__(self, message):
        super(UnknownApplicationException, self).__init__(message)
        self.timeout = message
