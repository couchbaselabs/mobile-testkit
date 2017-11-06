import ConfigParser
from CBLClient import Client
from CBLArgs import Args
from keywords.utils import log_info


class TestCase:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    ###################
    #  - Database -   #
    ###################

    def database_create(self, name):
        args = Args()
        args.setString("name", name)

        return self._client.invokeMethod("database_create", args)

    def database_getName(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_getName", args)

    def database_getDocument(self, database, id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("id", id)

        return self._client.invokeMethod("database_getDocument", args)

    def database_save(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)

        self._client.invokeMethod("database_save", args)

    def database_delete(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)

        self._client.invokeMethod("database_delete", args)

    def database_contains(self, database, id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("id", id)

        return self._client.invokeMethod("database_contains", args)

    def database_addChangeListener(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_addChangeListener", args)

    def database_removeChangeListener(self, database, changeListener):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("changeListener", changeListener)

        self._client.invokeMethod("database_removeChangeListener", args)

    def databaseChangeListener_changesCount(self, changeListener):
        args = Args()
        args.setMemoryPointer("changeListener", changeListener)

        return self._client.invokeMethod("databaseChangeListener_changesCount", args)

    def databaseChangeListener_getChange(self, changeListener, index):
        args = Args()
        args.setMemoryPointer("changeListener", changeListener)
        args.setInt("index", index)

        return self._client.invokeMethod("databaseChangeListener_getChange", args)

    def databaseChange_getDocumentId(self, change):
        args = Args()
        args.setMemoryPointer("change", change)

        return self._client.invokeMethod("databaseChange_getDocumentId", args)

    def databaseChange_isDelete(self, change):
        args = Args()
        args.setMemoryPointer("change", change)

        return self._client.invokeMethod("databaseChange_isDelete", args)

    ################
    # - Document - #
    ################

    def document_create(self, dictionary=None, id=None):
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

    def document_getId(self, document):
        args = Args()
        args.setMemoryPointer("document", document)

        return self._client.invokeMethod("document_getId", args)

    def document_getString(self, document, prop):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("property", prop)

        return self._client.invokeMethod("document_getString", args)

    def document_setString(self, document, prop, string):
        args = Args()
        args.setMemoryPointer("document", document)
        args.setString("property", prop)
        args.setString("string", string)

        self._client.invokeMethod("document_setString", args)

    ###################
    #  - Dictionary - #
    ###################

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

    ##############
    # - Memory - #
    ##############

    def release(self, object):
        self._client.release(object)
