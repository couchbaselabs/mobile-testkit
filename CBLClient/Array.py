from CBLClient.Client import Client
from CBLClient.Args import Args


class Array(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, array=None):
        args = Args()
        if array:
            args.setMemoryPointer("content_array", array)
        return self._client.invokeMethod("array_create", args)

    def setString(self, array, key, value):
        args = Args()
        args.setMemoryPointer("array", array)
        args.setInt("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("array_setString", args)

    def getString(self, array, key):
        args = Args()
        args.setMemoryPointer("array", array)
        args.setInt("key", key)
        return self._client.invokeMethod("array_getString", args)

    def addString(self, array, value):
        args = Args()
        args.setMemoryPointer("array", array)
        args.setString("value", value)
        return self._client.invokeMethod("array_addString", args)

    def addDictionary(self, array, value):
        args = Args()
        args.setMemoryPointer("array", array)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("array_addDictionary", args)

    def getArray(self, array, key):
        args = Args()
        args.setMemoryPointer("array", array)
        args.setInt("key", key)
        return self._client.invokeMethod("array_getArray", args)
