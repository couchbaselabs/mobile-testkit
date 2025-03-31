import json

from requests import Session
from requests import Response
from CBLClient.ValueSerializer import ValueSerializer
from CBLClient.Args import Args
from keywords.utils import log_info


class Client(object):

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = Session()

    def invokeMethod(self, method, args=None, ignore_deserialize=False):
        resp = Response()
        try:
            # Create body from args
            body = {}
            url = self.base_url + "/" + method

            if args:
                for k, v in args:
                    val = ValueSerializer.serialize(v)
                    body[k] = val

            # Create connection to method endpoint
            headers = {"Content-Type": "application/json"}
            self.session.headers = headers
            resp = self.session.post(url, data=json.dumps(body))

            # Log full response details for debugging
            log_info(f"Request URL: {url}")
            log_info(f"Request Body: {json.dumps(body, indent=2)}")
            log_info(f"Response Code: {resp.status_code}")
            log_info(f"Raw Response Content: {resp.content}")

            resp.raise_for_status()

            if resp.status_code == 200:
                result = resp.content
                if isinstance(result, bytes):
                    result = result.decode('utf8', 'ignore')

                # Print full message regardless of length
                log_info("Full Server Response: {}".format(result))

                # Check for null or invalid configs
                if "@null" in result or "null_java" in result:
                    raise Exception(f"Invalid DB Configuration: {result}")

                # Deserialize properly
                return ValueSerializer.deserialize(result)

        except Exception as err:
            error_message = f"Exception: {str(err)}"
            if resp.content:
                cont = resp.content
                if isinstance(resp.content, bytes):
                    cont = resp.content.decode('utf8', 'ignore')
                error_message += f"\nServer Response: {cont}"
            raise Exception(error_message)

    def release(self, obj):
        args = Args()
        args.setMemoryPointer("object", obj)
        self.invokeMethod("release", args)

    class MethodInvocationException(RuntimeError):
        _responseCode = None
        _responseMessage = None

        def __init__(self, responseCode, responseMessage):
            super(responseMessage)
            self._responseCode = responseCode
            self._responseMessage = responseMessage

        def getResponseCode(self):
            return self._responseCode

        def getResponseMessage(self):
            return self._responseMessage
