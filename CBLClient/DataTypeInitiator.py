from Client import Client
from Args import Args
from keywords.utils import log_info


class DataTypeInitiator:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def setDate(self):
        return self._client.invokeMethod("datatype_setDate")

    def setDouble(self, value):
        args = Args()
        args.setString("value", value)
        return self._client.invokeMethod("datatype_setDouble", args)

    def setFloat(self, value):
        args = Args()
        args.setString("value", value)
        return self._client.invokeMethod("datatype_setFloat", args)

    def compare(self, first, second):
        args = Args()
        args.setMemoryPointer("first", first)
        args.setMemoryPointer("second", second)
        return self._client.invokeMethod("datatype_compare", args)

    def hashMap(self):
        return self._client.invokeMethod("datatype_hashMap")

    def get(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("datatype_get", args)

    def put(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setString("value", value)
        self._client.invokeMethod("datatype_put", args)