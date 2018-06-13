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
        args.setFloat("value", value)
        return self._client.invokeMethod("datatype_setDouble", args)

    def setFloat(self, value):
        args = Args()
        args.setFloat("value", value)
        return self._client.invokeMethod("datatype_setFloat", args)

    def setLong(self, value):
        args = Args()
        args.setLong("value", value)
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

    def compareDate(self, date1, date2):
        args = Args()
        args.setMemoryPointer("date1", date1)
        args.setMemoryPointer("date2", date2)
        return self._client.invokeMethod("datatype_compareDate", args)

    def compareDouble(self, double1, double2):
        args = Args()
        args.setMemoryPointer("double1", double1)
        args.setMemoryPointer("double2", double2)
        return self._client.invokeMethod("datatype_compareDouble", args)

    def compareLong(self, long1, long2):
        args = Args()
        args.setMemoryPointer("long1", long1)
        args.setMemoryPointer("long2", long2)
        return self._client.invokeMethod("datatype_compareLong", args)
