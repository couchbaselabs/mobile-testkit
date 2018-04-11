from CBLClient.Client import Client


class Utils:
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def release(self, obj):
        # Release memory on the server
        if isinstance(obj, list):
            for i in obj:
                self._client.release(i)
        else:
            self._client.release(obj)

    def flushMemory(self):
        return self._client.invokeMethod("flushMemory")
