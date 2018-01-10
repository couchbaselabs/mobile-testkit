from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Utils:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def release(self, obj):
        # Release memory on the server
        if isinstance(obj, list):
            for i in obj:
                self._client.release(i)
        else:
            self._client.release(obj)

    def flushMemory(self):
        return self._client.invokeMethod("flushMemory")
