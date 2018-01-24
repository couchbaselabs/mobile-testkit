import uuid

from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info
from keywords import types
from libraries.data import doc_generators
from Document import Document
import uuid
import json


class Database(object):
    _db = None
    _baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def configure(self, directory=None, conflictResolver=None, encryptionKey=None, fileProtection=None):
        args = Args()
        if directory is not None:
            args.setString("directory", directory)
        if conflictResolver is not None:
            args.setMemoryPointer("conflictResolver", conflictResolver)
        if encryptionKey is not None:
            args.setMemoryPointer("encryptionKey", encryptionKey)
        if fileProtection is not None:
            args.setMemoryPointer("fileProtection", fileProtection)
        return self._client.invokeMethod("databaseConfiguration_configure", args)

    def create(self, name, config):
        args = Args()
        args.setString("name", name)
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("database_create", args)

    def delete(self, name=None, path=None, database=None, document=None):
        args = Args()
        if database:
            args.setMemoryPointer("database", database)
            if document is not None:
                args.setMemoryPointer("document", document)
        elif name and path:
            args.setString("name", name)
            args.setString("path", path)
        else:
            raise Exception("Either pass database and document or pass \
            name and path to delete the document.")
        return self._client.invokeMethod("database_deleteDocument", args)

    def purge(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        if document is not None:
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
        if doc_id is not None:
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
        if document is not None:
            args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_save", args)

    def saveDocuments(self, database, documents):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setDictionary("documents", documents)
        return self._client.invokeMethod("database_saveDocuments", args)

    def updateDocuments(self, database, documents):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setDictionary("documents", documents)
        return self._client.invokeMethod("database_updateDocuments", args)

    def updateDocument(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setDictionary("document", document)
        return self._client.invokeMethod("database_updateDocument", args)

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

    def removeChangeListener(self, database, change_listener):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("database_removeChangeListener", args)

    def databaseChangeListener_changesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("database_databaseChangeListener_changesCount", args)

    def databaseChangeListener_getChange(self, change_listener, index):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
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

    def getIndexes(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_getIndexes", args)

    def exists(self, name, directory=None):
        args = Args()
        args.setString("name", name)
        args.setMemoryPointer("directory", directory)
        return self._client.invokeMethod("database_exists", args)

    def deleteDBbyName(self, name):
        args = Args()
        args.setString("name", name)
        return self._client.invokeMethod("database_deleteDBbyName", args)

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

    def update_bulk_docs(self, database, number_of_updates=1):
  
        updated_docs = {}
        doc_ids = self.getDocIds(database)
        
        docs = self.getDocuments(database, doc_ids)
        for i in xrange(number_of_updates):
            print "docs in update bulk docs updating in ", i
            for doc in docs:
                doc_body = docs[doc]
                try:
                    doc_body["updates-cbl"]
                except Exception:
                    doc_body["updates-cbl"] = 0

                doc_body["updates-cbl"] = doc_body["updates-cbl"] + 1
                updated_docs[doc] = doc_body

            self.updateDocuments(database, updated_docs)

    def update_all_docs_individually(self, database, num_of_updates=1):

        doc_ids = self.getDocIds(database)
        docs = self.getDocuments(database, doc_ids)
        doc_obj = Document(self._baseUrl)
        for i in xrange(num_of_updates):
            for doc_id in doc_ids:
                print("doc id invidually is ", doc_id)
                doc_mem = self.getDocument(database, doc_id)
                doc_mut = doc_obj.toMutable(doc_mem)
                doc_body = doc_obj.toDictionary(doc_mut)
                print("doc invidually is ", doc_body)
                try:
                    doc_body["updates-cbl"]
                except Exception:
                    doc_body["updates-cbl"] = 0

                doc_body["updates-cbl"] = doc_body["updates-cbl"] + 1
                doc = doc_obj.setData(doc_mut, doc_body)
                self.updateDocument(database, doc)


    def deleteDBIfExists(self, db_name):
        if self.exists(db_name):
            self.deleteDBbyName(db_name)

    def deleteDBIfExistsCreateNew(self, db_name):
        if self.exists(db_name):
            self.deleteDBbyName(db_name)
        return self.create(db_name)