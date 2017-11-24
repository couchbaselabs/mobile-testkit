from CBLClient.Client import Client
from CBLClient.Args import Args


class Database:
    _db = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, name):
        args = Args()
        args.setString("name", name)
        self._db = self._client.invokeMethod("database_create", args)
        return self._db

    def delete(self, name=None, path=None, database= None, document=None):
        args = Args()
        if document and database:
            args.setMemoryPointer("database", database)
            args.setMemoryPointer("document", document)
        elif name and path:
            args.setString("name", name)
            args.setString("path", path)
        else:
            raise Exception("Either pass database and document or pass "\
                            "name and path to delete the document.")
        return self._client.invokeMethod("database_delete", args)

    def purge(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_purge", args)

    def deleteDB(self, database):
        args = Args()
        args.setString("database", database)
        return self._client.invokeMethod("database_deleteDB", args)

    def close(self, database):
        args = Args()
        args.setString("database", database)
        return self._client.invokeMethod("database_close", args)

    def path(self, database):
        args = Args()
        args.setString("database", database)
        return self._client.invokeMethod("database_path", args)

    def getName(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getName", args)

    def getPath(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getPath", args)

    def getDocument(self, database, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("id", doc_id)
        return self._client.invokeMethod("database_getDocument", args)

    def save(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)
        self._client.invokeMethod("database_save", args)

    def contains(self, database, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("id", doc_id)
        return self._client.invokeMethod("database_contains", args)

    def getCount(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getCount", args)

    def addChangeListener(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_addChangeListener", args)

    def removeChangeListener(self, database, changeListener):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("changeListener", changeListener)
        self._client.invokeMethod("database_removeChangeListener", args)

    def databaseChangeListener_changesCount(self, changeListener):
        args = Args()
        args.setMemoryPointer("changeListener", changeListener)
        return self._client.invokeMethod("database_databaseChangeListener_changesCount", args)

    def databaseChangeListener_getChange(self, changeListener, index):
        args = Args()
        args.setMemoryPointer("changeListener", changeListener)
        args.setInt("index", index)
        return self._client.invokeMethod("database_databaseChangeListener_getChange", args)

    def databaseChange_getDocumentId(self, change):
        args = Args()
        args.setMemoryPointer("change", change)
        return self._client.invokeMethod("database_databaseChange_getDocumentId", args)

    def addDocuments(self, database, data):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_addDocuments", args, post_data=data)

    def getDocIds(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getDocIds", args)

    def getDocuments(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getDocuments", args)
