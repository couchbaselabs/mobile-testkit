from CBLClient.Client import Client
from CBLClient.Args import Args


class Collection(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def getDocIds(self, collection, limit=1000, offset=0):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setInt("limit", limit)
        args.setInt("offset", offset)
        return self._client.invokeMethod("collection_getDocIds", args)

    def collectionName(self, collection):
        args = Args()
        args.setMemoryPointer("collection", collection)
        return self._client.invokeMethod("collection_getCollectionName", args)

    def allCollection(self, database, scopeName):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("scopeName", scopeName)
        return self._client.invokeMethod("collection_collectionNames", args)

    def documentCount(self, collection):
        args = Args()
        args.setMemoryPointer("collection", collection)
        return self._client.invokeMethod("collection_documentCount", args)

    def saveDocument(self, collection, document):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setMemoryPointer("document", document)
        return self._client.invokeMethod("collection_saveDocument", args)

    def collectionScope(self, collection):
        args = Args()
        args.setMemoryPointer("collection", collection)
        return self._client.invokeMethod("collection_collectionScope", args)

    def getDocuments(self, collection, ids, encrypted=False):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setArray("ids", ids)
        args.setBoolean("encrypted", encrypted)
        return self._client.invokeMethod("collection_getDocuments", args)

    def updateDocument(self, collection, data, doc_id):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setDictionary("data", data)
        args.setString("id", doc_id)
        return self._client.invokeMethod("collection_updateDocument", args)

    def getDocument(self, collection, docId):
        args = Args()
        args.setString("docId", docId)
        args.setMemoryPointer("collection", collection)
        return self._client.invokeMethod("collection_getDocument", args)

    def deleteDocument(self, collection, doc):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setMemoryPointer("document", doc)
        return self._client.invokeMethod("collection_deleteDocument", args)

    def purgeDocument(self, collection, doc):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setMemoryPointer("document", doc)
        return self._client.invokeMethod("collection_purgeDocument", args)

    def purgeDocumentById(self, collection, docId):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("docId", docId)
        return self._client.invokeMethod("collection_purgeDocumentID", args)

    def getDocumentExpiration(self, collection, docId):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("docId", docId)
        return self._client.invokeMethod("collection_getDocumentExpiration", args)

    def setDocumentExpiration(self, collection, docId, expirationTime):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("docId", docId)
        args.setInt("expiration", expirationTime)
        return self._client.invokeMethod("collection_setDocumentExpiration", args)

    def getMutableDocument(self, collection, docId):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("docId", docId)
        return self._client.invokeMethod("collection_getMutableDocument", args)

    def createValueIndex(self, collection, name, expression):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("name", name)
        args.setString("expression", expression)
        return self._client.invokeMethod("collection_createValueIndex", args)

    def iosCreateValueIndex(self, collection, name, expression):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("name", name)
        args.setArray("expression", expression)
        return self._client.invokeMethod("collection_createValueIndex", args)

    def deleteIndex(self, collection, name):
        args = Args()
        args.setMemoryPointer("collection", collection)
        args.setString("name", name)
        return self._client.invokeMethod("collection_deleteIndex", args)

    def getIndexNames(self, collection):
        args = Args()
        args.setMemoryPointer("collection", collection)
        return self._client.invokeMethod("collection_getIndexNames", args)

    def collectionSaveDocuments(self, database, documents, collection):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setMemoryPointer("collection", collection)
        args.setDictionary("documents", documents)
        return self._client.invokeMethod("collection_saveDocuments", args)
    
    def getCollectionInstances(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("collection_collectionInstances", args)
