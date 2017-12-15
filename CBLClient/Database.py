from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info
from libraries.data import doc_generators
from keywords import types
import uuid
import json

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

    def delete(self, name=None, path=None, database=None, document=None):
        args = Args()
        if database:
            args.setMemoryPointer("database", database)
            if document != None:
                args.setMemoryPointer("document", document)
        elif name and path:
            args.setString("name", name)
            args.setString("path", path)
        else:
            raise Exception("Either pass database and document or pass \
            name and path to delete the document.")
        return self._client.invokeMethod("database_delete", args)

    def purge(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        if document != None:
            args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_purge", args)

    def deleteDB(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_deleteDB", args)

    def close(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
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

    def getDocument(self, database, doc_id=None):
        args = Args()
        args.setMemoryPointer("database", database)
        if doc_id != None:
            args.setString("id", doc_id)
        return self._client.invokeMethod("database_getDocument", args)

    def getDocuments(self, database, ids):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setArray("ids", ids)
        return self._client.invokeMethod("database_getDocuments", args)

    def saveDocument(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        if document != None:
            args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_saveDocument", args)

    def saveDocuments(self, database, documents):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setDictionary("documents", documents)
        return self._client.invokeMethod("database_saveDocuments", args)

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
        return self._client.invokeMethod("database_removeChangeListener", args)

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

    def getDocIds(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getDocIds", args)

    def create_value_index(self, database, prop):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("property", prop)
        return self._client.invokeMethod("create_value_index", args)

    def create_bulk_docs(self, number, id_prefix, db, channels=None, generator=None, attachments_generator=None):
        """
        if id_prefix == None, generate a uuid for each doc

        Add a 'number' of docs with a prefix 'id_prefix' using the provided generator from libraries.data.doc_generators.
        ex. id_prefix=testdoc with a number of 3 would create 'testdoc_0', 'testdoc_1', and 'testdoc_2'
        """
        added_docs = {}
        if channels is not None:
            types.verify_is_list(channels)

        log_info("PUT {} docs to with prefix {}".format(number, id_prefix))

        for i in xrange(number):

            if generator == "four_k":
                doc_body = doc_generators.four_k()
            elif generator == "simple_user":
                doc_body = doc_generators.simple_user()
            else:
                doc_body = doc_generators.simple()

            if channels is not None:
                doc_body["channels"] = channels

            if attachments_generator:
                types.verify_is_callable(attachments_generator)
                attachments = attachments_generator()
                doc_body["_attachments"] = {att.name: {"data": att.data} for att in attachments}

            if id_prefix is None:
                doc_id = str(uuid.uuid4())
            else:
                doc_id = "{}_{}".format(id_prefix, i)

            doc_body["_id"] = doc_id
            added_docs[doc_id] = doc_body
            
        self.saveDocuments(db, added_docs)


