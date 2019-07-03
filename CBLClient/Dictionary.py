from CBLClient.Client import Client
from CBLClient.Args import Args


class Dictionary(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, dictionary=None):
        args = Args()
        if dictionary:
            args.setMemoryPointer("content_dict", dictionary)
        return self._client.invokeMethod("dictionary_create", args)

    def toMutableDictionary(self, dictionary):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("dictionary_toMutableDictionary", args)

    def getString(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getString", args)

    def setString(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("dictionary_setString", args)

    def getKeys(self, dictionary):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("dictionary_getKeys", args)

    def contains(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setMemoryPointer("key", key)
        return self._client.invokeMethod("dictionary_contains", args)

    def count(self, dictionary):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("dictionary_count", args)

    def getArray(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getArray", args)

    def setArray(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setArray", args)

    def getBlob(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getBlob", args)

    def setBlob(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setBlob", args)

    def getBoolean(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getBoolean", args)

    def setBoolean(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setBoolean("value", value)
        return self._client.invokeMethod("dictionary_setBoolean", args)

    def getDate(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getDate", args)

    def setDate(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setDate", args)

    def getDictionary(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getDictionary", args)

    def setDictionary(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setDictionary", args)

    def getDouble(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getDouble", args)

    def setDouble(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setDouble", args)

    def getFloat(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getFloat", args)

    def setFloat(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setFloat", args)

    def getLong(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getLong", args)

    def setLong(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setLong("value", value)
        return self._client.invokeMethod("dictionary_setLong", args)

    def getNumber(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getNumber", args)

    def setNumber(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setMemoryPointer("value", value)
        return self._client.invokeMethod("dictionary_setNumber", args)

    def getInt(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_getInt", args)

    def setInt(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setInt("value", value)
        return self._client.invokeMethod("dictionary_setInt", args)

    def remove(self, dictionary, key):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        return self._client.invokeMethod("dictionary_remove", args)

    def iterator(self, dictionary):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("dictionary_iterator", args)

    def toMap(self, dictionary):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("dictionary_toMap", args)

    def setValue(self, dictionary, key, value):
        args = Args()
        args.setMemoryPointer("dictionary", dictionary)
        args.setString("key", key)
        args.setInt("value", value)
        return self._client.invokeMethod("dictionary_setValue", args)
