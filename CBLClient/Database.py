import uuid

from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info
from keywords import types
from libraries.data import doc_generators
from Document import Document


class Database(object):
    _db = None
    _baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def configure(self, directory=None, conflictResolver=None, password=None):
        args = Args()
        if directory is not None:
            args.setString("directory", directory)
        if conflictResolver is not None:
            args.setMemoryPointer("conflictResolver", conflictResolver)
        if password is not None:
            args.setMemoryPointer("password", password)
        return self._client.invokeMethod("databaseConfiguration_configure", args)

    def create(self, name, config=None):
        args = Args()
        args.setString("name", name)
        if config:
            args.setMemoryPointer("config", config)
        return self._client.invokeMethod("database_create", args)

    def delete(self, database=None, document=None):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_delete", args)

    def purge(self, database, document):
        args = Args()
        args.setMemoryPointer("database", database)
        if document is not None:
            args.setMemoryPointer("document", document)
        return self._client.invokeMethod("database_purge", args)

    def deleteDB(self, database, name=None, path=None):
        args = Args()
        args.setMemoryPointer("database", database)
        if database:
            args.setMemoryPointer("database", database)
            if name is not None and path is not None:
                args.setString("name", name)
                args.setString("path", path)
        else:
            raise Exception("Should pass atleast database to delete")
        return self._client.invokeMethod("database_deleteDB", args)

    def close(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_close", args)

    def compact(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("database_compact", args)

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

    def updateDocument(self, database, data, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setDictionary("data", data)
        args.setString("id", doc_id)
        return self._client.invokeMethod("database_updateDocument", args)

#     def contains(self, database, doc_id):
#         args = Args()
#         args.setMemoryPointer("database", database)
#         args.setString("id", doc_id)
#         return self._client.invokeMethod("database_contains", args)

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
        return self._client.invokeMethod("database_databaseChangeListenerChangesCount", args)

    def databaseChangeListener_getChange(self, change_listener, index):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        args.setInt("index", index)
        return self._client.invokeMethod("database_databaseChangeListenerGetChange", args)

    def databaseChange_getDocumentId(self, change):
        args = Args()
        args.setMemoryPointer("change", change)
        return self._client.invokeMethod("database_databaseChangeGetDocumentId", args)

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

    def setEncryptionKey(self, database, password):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("password", password)
        return self._client.invokeMethod("database_setEncryptionKey", args)

    def saveDocumentWithConcurrency(self, database, document, concurrencyControlType):
        args = Args()
        args.setMemoryPointer("database", database)
        if document is not None:
            args.setMemoryPointer("document", document)
        if concurrencyControlType is not None:
            args.setString("concurrencyControlType", concurrencyControlType)
        return self._client.invokeMethod("database_saveWithConcurrency", args)

    def deleteDocumentWithConcurrency(self, database, document, concurrencyControlType):
        args = Args()
        args.setMemoryPointer("database", database)
        if document is not None:
            args.setMemoryPointer("document", document)
        if concurrencyControlType is not None:
            args.setString("concurrencyControlType", concurrencyControlType)
        return self._client.invokeMethod("database_deleteWithConcurrency", args)


#     Not implemented on server
#     def create_value_index(self, database, prop):
#         args = Args()
#         args.setMemoryPointer("database", database)
#         args.setString("property", prop)
#         return self._client.invokeMethod("create_valueIndex", args)

    def create_bulk_docs(self, number, id_prefix, db, channels=None, generator=None, attachments_generator=None, id_start_num=0):
        """
        if id_prefix == None, generate a uuid for each doc

        Add a 'number' of docs with a prefix 'id_prefix' using the provided generator from libraries.data.doc_generators.
        ex. id_prefix=testdoc with a number of 3 would create 'testdoc_0', 'testdoc_1', and 'testdoc_2'
        """
        added_docs = {}
        if channels is not None:
            types.verify_is_list(channels)

        log_info("PUT {} docs to with prefix {}".format(number, id_prefix))

        for i in xrange(id_start_num, id_start_num + number):

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

    def delete_bulk_docs(self, database, doc_ids=[]):
        if not doc_ids:
            doc_ids = self.getDocIds(database)
        args = Args()
        args.setMemoryPointer("database", database)
        args.setArray("doc_ids", doc_ids)
        return self._client.invokeMethod("database_deleteBulkDocs", args)

    def update_bulk_docs(self, database, number_of_updates=1, doc_ids=[]):

        updated_docs = {}
        if not doc_ids:
            doc_ids = self.getDocIds(database)
        log_info("updating bulk docs")

        docs = self.getDocuments(database, doc_ids)
        if len(docs) < 1:
            raise Exception("cbl docs are empty , cannot update docs")
        for _ in xrange(number_of_updates):
            for doc in docs:
                doc_body = docs[doc]
                if "updates-cbl" not in doc_body:
                    doc_body["updates-cbl"] = 0
                doc_body["updates-cbl"] = doc_body["updates-cbl"] + 1
                updated_docs[doc] = doc_body
            self.updateDocuments(database, updated_docs)

    def update_all_docs_individually(self, database, num_of_updates=1):
        doc_ids = self.getDocIds(database)
        doc_obj = Document(self._baseUrl)
        for i in xrange(num_of_updates):
            for doc_id in doc_ids:
                doc_mem = self.getDocument(database, doc_id)
                doc_mut = doc_obj.toMutable(doc_mem)
                doc_body = doc_obj.toMap(doc_mut)
                try:
                    doc_body["updates-cbl"]
                except Exception:
                    doc_body["updates-cbl"] = 0

                doc_body["updates-cbl"] = doc_body["updates-cbl"] + 1
                self.updateDocument(database, doc_body, doc_id)

    def deleteDBIfExists(self, db_name):
        if self.exists(db_name):
            self.deleteDBbyName(db_name)

    def deleteDBIfExistsCreateNew(self, db_name):
        if self.exists(db_name):
            self.deleteDBbyName(db_name)
        return self.create(db_name)

    def cbl_delete_bulk_docs(self, cbl_db):
        cbl_doc_ids = self.getDocIds(cbl_db)
        for id in cbl_doc_ids:
            doc = self.getDocument(cbl_db, id)
            self.delete(cbl_db, doc)

    def getBulkDocs(self, cbl_db):
        cbl_doc_ids = self.getDocIds(cbl_db)
        docs = self.getDocuments(cbl_db, cbl_doc_ids)
        return docs
