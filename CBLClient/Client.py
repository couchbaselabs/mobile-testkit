import json

from requests import Session
from CBLClient.ValueSerializer import ValueSerializer
from CBLClient.Args import Args
from keywords.utils import log_info

class Client(object):

    def __init__(self, baseUrl):
        self.baseurl = baseUrl
        self.session = Session()

    def invokeMethod(self, method, args):
        try:
            # Create query string from args.
            body = {}
            url = self.baseurl + "/" + method

            if args:
                #log_info("args: {}".format(args.getArgs()))

                for k, v in args:
                    #log_info("k={}, v={}".format(k, v))
                    #log_info("instance type of v: {}".format(type(v)))
                    val = ValueSerializer.serialize(v)
                    #log_info("k={}, val={}".format(k, val))
                    body[k] = val

            log_info("body: {}".format(body))
            log_info("URL: {}".format(url))
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
        except RuntimeError as err:
            raise err
        except Exception as err:
            raise  err# RuntimeError(e)

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
