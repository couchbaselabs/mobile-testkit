from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Document:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, doc_id=None, dictionary=None,):
        args = Args()

        if doc_id and dictionary:
            args.setString("id", doc_id)
            args.setMemoryPointer("dictionary", dictionary)
            return self._client.invokeMethod("document_create", args)
        elif dictionary:
            args.setMemoryPointer("dictionary", dictionary)
            return self._client.invokeMethod("document_create", args)
        elif doc_id:
            args.setString("id", doc_id)
            return self._client.invokeMethod("document_create", args)
        else:
            return self._client.invokeMethod("document_create")

    def delete(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("document_delete", args)

    def getId(self, document):
        args = Args()
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("document_getId", args)

    def getString(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getString", args)

    def setString(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setString", args)

    def set(self,document, dictionary):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setMemoryPointer("dictionary", dictionary)
        return self._client.invokeMethod("document_set", args)

    def getKeys(self, document):
        args = Args()
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("document_getKeys", args)

    def contains(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setMemoryPointer("key", key)
        return self._client.invokeMethod("document_contains", args)

    def count(self, document):
        args = Args()
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("document_count", args)

    def get(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setMemoryPointer("key", key)
        return self._client.invokeMethod("document_get", args)

    
    def getArray(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setMemoryPointer("key", key)
        return self._client.invokeMethod("document_getArray", args)

    def setArray(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setArray", args)

    def getBlob(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getBlob", args)

    def setBlob(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setBlob", args)

    def getBoolean(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getBoolean", args)

    def setBoolean(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setBoolean("value", value)
        return self._client.invokeMethod("document_setBoolean", args)

    def getDate(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getDate", args)

    def setDate(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setDate", args)

    def getDictionary(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getDictionary", args)

    def setDictionary(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setDictionary", args)

    def getDouble(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getDouble", args)

    def setDouble(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setDouble", args)

    def getFloat(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getFloat", args)

    def setFloat(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setFloat", args)

    def getLong(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getLong", args)

    def setLong(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setLong", args)

    def getObject(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getObject", args)

    def setObject(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setObject", args)

    def getNumber(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getNumber", args)

    def setNumber(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setNumber", args)

    def getInt(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_getInt", args)

    def setInt(self, document, key, value):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        args.setString("value", value)
        return self._client.invokeMethod("document_setInt", args)

    def remove(self, document, key):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("key", key)
        return self._client.invokeMethod("document_removeKey", args)

    def toMap(self, document):
        args = Args()
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("document_toMap", args)
