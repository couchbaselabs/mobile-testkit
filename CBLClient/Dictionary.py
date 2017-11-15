from Client import Client
from Args import Args
from keywords.utils import log_info


class Dictionary:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def dictionary_create(self):
        return self._client.invokeMethod("dictionary_create")

    def dictionary_get(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)

        return self._client.invokeMethod("dictionary_get", args)

    def dictionary_put(self, dictionary, key, string):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setString("string", string)

        self._client.invokeMethod("dictionary_put", args)
