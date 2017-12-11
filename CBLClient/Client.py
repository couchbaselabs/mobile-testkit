import json

from requests import Session
from ValueSerializer import ValueSerializer
from Args import Args
from keywords.utils import log_info


class Client:

    def __init__(self, baseUrl):
        self._baseUrl = baseUrl
        self.session = Session()

    def invokeMethod(self, method, args=None):
        try:
            # Create body from args.
            body = {}

            url = self._baseUrl + "/" + method

            if args:
                for k, v in args:
                    val = ValueSerializer.serialize(v)
                    body[k] = val

            # Create connection to method endpoint.
            headers = {"Content-Type": "application/json"}
            self.session.headers = headers
            resp = self.session.post(url, data=json.dumps(body))
            resp.raise_for_status()

            # Process response.
            responseCode = resp.status_code

            if responseCode == 200:
                result = resp.content
                log_info("Got response: {}".format(result))
                return ValueSerializer.deserialize(result)
        except RuntimeError as e:
            raise e
        except Exception as e:
            raise  # RuntimeError(e)

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
