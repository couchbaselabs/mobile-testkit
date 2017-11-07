import urllib
from requests import Session
from CBLValueSerializer import ValueSerializer
from CBLArgs import Args
from keywords.utils import log_info


class Client:
    baseUrl = None
    session = Session()

    def __init__(self, baseUrl):
        self._baseUrl = baseUrl

    def invokeMethod(self, method, args=None):
        try:
            # Create query string from args.
            query = ""

            if args:
                for k, v in args:
                    query += "?" if len(query) == 0 else "&"
                    k_v = "{}={}".format(k, ValueSerializer.serialize(v))
                    query += k_v

            # Create connection to method endpoint.
            url = self._baseUrl + "/" + method + query
            log_info("URL: {}".format(url))
            resp = self.session.post(url)
            resp.raise_for_status()

            # Process response.
            responseCode = resp.status_code
            if responseCode == 200:
                result = resp.content
                log_info("result: {}".format(result))
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
