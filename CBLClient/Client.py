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

    def invokeMethod(self, method, args=None):
        resp = Response()
        try:
            # Create body from args.
            body = {}

            url = self.base_url + "/" + method

            if args:
                # log_info("args: {}".format(args.getArgs()))

                for k, v in args:
                    val = ValueSerializer.serialize(v)
                    body[k] = val

            log_info("body: {}".format(body))
            log_info("URL: {}".format(url))
            # Create connection to method endpoint.
            headers = {"Content-Type": "application/json"}
            self.session.headers = headers
            log_info("body is {}".format(body))
            resp = self.session.post(url, data=json.dumps(body))
            resp.raise_for_status()
            responseCode = resp.status_code

            if responseCode == 200:
                result = resp.content
                if len(result) < 25:
                    # Only print short messages
                    log_info("Got response: {}".format(result))
                return ValueSerializer.deserialize(result)
        except RuntimeError as err:
            raise err
        except Exception as err:
            # resp can't be accessed here
            return err, resp.content

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
