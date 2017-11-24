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

    def create(self, dictionary=None, id=None):
        args = Args()

        if id and dictionary:
            args.setString("id", id)
            args.setMemoryPointer("dictionary", dictionary)
            return self._client.invokeMethod("document_create", args)
        elif dictionary:
            args.setMemoryPointer("dictionary", dictionary)
            return self._client.invokeMethod("document_create", args)
        elif id:
            args.setString("id", id)
            return self._client.invokeMethod("document_create", args)
        else:
            return self._client.invokeMethod("document_create")

    def delete(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)

        self._client.invokeMethod("document_delete", args)

    def getId(self, document):
        args = Args()
        args.setMemoryPointer("document", document)

        return self._client.invokeMethod("document_getId", args)

    def getString(self, document, prop):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("property", prop)

        return self._client.invokeMethod("document_getString", args)

    def setString(self, document, prop, string):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("property", prop)
        args.setString("string", string)

        self._client.invokeMethod("document_setString", args)
