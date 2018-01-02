from CBLClient.Client import Client
from CBLClient.Args import Args

class DataTypeInitiator(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(self.base_url)

    def setDate(self):
        args = Args()
        return self._client.invokeMethod("datatype_setDate", args)

    def setDouble(self, value):
        args = Args()
        args.setString("value", value)
        return self._client.invokeMethod("datatype_setDouble", args)

    def setFloat(self, value):
        args = Args()
        args.setString("value", value)
        return self._client.invokeMethod("datatype_setFloat", args)

    def setLong(self, value):
        args = Args()
        args.setString("value", value)
        return self._client.invokeMethod("datatype_setLong", args)

    def compare(self, first, second):
        args = Args()
        args.setMemoryPointer("first", first)
        args.setMemoryPointer("second", second)
        return self._client.invokeMethod("datatype_compare", args)

    def compareHashMap(self, first, second):
        args = Args()
        args.setDictionary("first", first)
        args.setDictionary("second", second)
        return self._client.invokeMethod("datatype_compareHashMap", args)

    def hashMap(self):
        args = Args()
        return self._client.invokeMethod("datatype_hashMap", args)

    def get(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("datatype_get", args)

    def put(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        if isinstance(value, str):
            args.setString("value", value)
        elif isinstance(value, bool):
            args.setBoolean("value", value)
        elif isinstance(value, int):
            args.setInt("value", value)
        self._client.invokeMethod("datatype_put", args)
