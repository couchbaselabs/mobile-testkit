from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Database:
    _db = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def database_create(self, name):
        args = Args()
        args.setString("name", name)
        self._db = self._client.invokeMethod("database_create", args)

        return self._db

    def database_delete(self, name, path):
        args = Args()
        args.setString("name", name)
        args.setString("path", path)

        return self._client.invokeMethod("database_delete", args)

    def database_close(self, database):
        args = Args()
        args.setString("database", database)

        return self._client.invokeMethod("database_close", args)

    def database_path(self, database):
        args = Args()
        args.setString("database", database)

        return self._client.invokeMethod("database_path", args)

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

    def database_contains(self, database, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("id", doc_id)

        return self._client.invokeMethod("database_contains", args)

    def database_docCount(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_docCount", args)

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

    def database_addDocuments(self, database, data):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_addDocuments", args, post_data=data)

    def database_getDocIds(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_getDocIds", args)

    def database_getDocuments(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("database_getDocuments", args)
