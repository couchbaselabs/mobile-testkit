import pytest
from keywords.utils import random_string, log_info

# These test cases are only for checking the framework


@pytest.mark.usefixtures("class_init")
class TestDatabase(object):

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).upper(),
    ])
    # Test to check default scope name in CBL.
    def test_defaultScope(self, db_name):
        db = self.db_obj.create(db_name)
        scope = self.db_obj.defaultScope(db)
        scopeName = self.scope_obj.scopeName(scope)
        expected_name = "_default"
        assert scopeName == expected_name, "Default scope not present"

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).upper(),
    ])
    # Test to check default collection name in CBL
    def test_defaultCollection(self, db_name):
        db = self.db_obj.create(db_name)
        collection = self.db_obj.defaultCollection(db)
        collectionName = self.collection_obj.collectionName(collection)
        expected_name = '_default'
        assert collectionName == expected_name, "Wrong Default Collection Name"

    @pytest.mark.parametrize("db_name, collectionName", [
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
    ])
    def test_createCollection(self, db_name, collectionName):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        created_collection_name = self.collection_obj.collectionName(created_collection)
        assert created_collection_name == collectionName, "Collection name doesn't match"

    @pytest.mark.parametrize("db_name, collectionName, no_of_document", [
        (random_string(6), random_string(6), 9),
        (random_string(6), random_string(6), 99),
        (random_string(6), random_string(6), 999),
    ])
    def test_documentCount(self, db_name, collectionName, no_of_document):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        for i in range(0, no_of_document):
            doc = self.doc_obj.create()
            self.collection_obj.saveDocument(created_collection, doc)
        document_count = self.collection_obj.documentCount(created_collection)
        assert document_count == no_of_document, "Document count doesn't match"

    # Test to delete collection.
    @pytest.mark.parametrize("db_name, collectionName", [
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
    ])
    def test_deleteCollection(self, db_name, collectionName):
        db = self.db_obj.create(db_name)
        scopeName = "_default"
        self.db_obj.createCollection(db, collectionName, scopeName)
        collectionNames = self.db_obj.collectionsInScope(db, scopeName)
        self.db_obj.deleteCollection(db, collectionName, scopeName)
        collectionNames2 = self.db_obj.collectionsInScope(db, scopeName)
        deleted_item = []
        for i in collectionNames:
            if i not in collectionNames2:
                deleted_item.append(i)
        assert len(deleted_item) == 1, "Deleted more than or less than one collection"
        assert deleted_item[0] == (collectionName), "Incorrect deletion"

    # Test to get collection object using scope name and collection name
    @pytest.mark.parametrize("db_name, collectionName", [
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
    ])
    def test_collectionObject(self, db_name, collectionName):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        self.db_obj.createCollection(db, collectionName, scopeName)
        created_Collection = self.db_obj.collectionObject(db, collectionName, scopeName)
        created_CollectionName = self.collection_obj.collectionName(created_Collection)
        assert created_CollectionName == collectionName, "Collection not created"

    # Test get scope object using collection object
    @pytest.mark.parametrize("db_name, collectionName", [
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(6), random_string(6)),
    ])
    def test_collectionScope(self, db_name, collectionName):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_Collection = self.db_obj.createCollection(db, collectionName, scopeName)
        scope = self.collection_obj.collectionScope(created_Collection)
        retrivedName = self.scope_obj.scopeName(scope)
        assert retrivedName == scopeName, "Incorrect Scope Object"

    @pytest.mark.parametrize("db_name, collectionName, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_getDocument(self, db_name, collectionName, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        retrived_doc = self.collection_obj.getDocument(created_collection, docId)
        retrived_docId = self.doc_obj.getId(retrived_doc)
        assert docId == retrived_docId, "Document retrival failed"

    @pytest.mark.parametrize("db_name, collectionName, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_deleteDocument(self, db_name, collectionName, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        retrived_doc = self.collection_obj.getDocument(created_collection, docId)
        assert self.collection_obj.deleteDocument(created_collection, retrived_doc) == True

    @pytest.mark.parametrize("db_name, collectionName, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_purgeDocument(self, db_name, collectionName, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        retrived_doc = self.collection_obj.getDocument(created_collection, docId)
        assert self.collection_obj.purgeDocument(created_collection, retrived_doc) == True

    @pytest.mark.parametrize("db_name, collectionName, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_purgeDocumentById(self, db_name, collectionName, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collectionName, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        retrived_doc = self.collection_obj.getDocument(created_collection, docId)
        retrived_docId = self.doc_obj.getId(retrived_doc)
        assert self.collection_obj.purgeDocumentById(created_collection, retrived_docId) == True

    @pytest.mark.parametrize("db_name, collection_name, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_documnetExpiration(self, db_name, collection_name, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        expiration_time = self.collection_obj.getDocumentExpiration(created_collection, docId)
        log_info(expiration_time)
        assert expiration_time == 0, "Incorrect default expiration time"

    @pytest.mark.parametrize("db_name, collection_name, docId, expirationTime", [
        (random_string(6), random_string(6), random_string(6), 99),
        # (random_string(6), random_string(6), random_string(6), 3),
        # (random_string(6), random_string(6), random_string(6), 5),
    ])
    def test_setDocumentExpiration(self, db_name, collection_name, docId, expirationTime):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        self.collection_obj.setDocumentExpiration(created_collection, docId, expirationTime)
        expiration_time = self.collection_obj.getDocumentExpiration(created_collection, docId)
        assert expiration_time == expirationTime, "Expiration time set failed"

    @pytest.mark.parametrize("db_name, collection_name, docId", [
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
    ])
    def test_getMutableDocument(self, db_name, collection_name, docId):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        doc = self.doc_obj.create(docId)
        self.collection_obj.saveDocument(created_collection, doc)
        assert self.collection_obj.getMutableDocument(created_collection, docId)

    @pytest.mark.parametrize("db_name, collection_name, name, expression", [
        (random_string(6), random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6), random_string(6)),
    ])
    def test_createValueIndex(self, db_name, collection_name, name, expression):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        assert self.collection_obj.createValueIndex(created_collection, name, expression)

    @pytest.mark.parametrize("db_name, collection_name, name, expression", [
        (random_string(6), random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6), random_string(6)),
        (random_string(6), random_string(6), random_string(6), random_string(6)),
    ])
    def test_deleteIndex(self, db_name, collection_name, name, expression):
        db = self.db_obj.create(db_name)
        scopeName = '_default'
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        assert self.collection_obj.createValueIndex(created_collection, name, expression)
        assert self.collection_obj.deleteIndex(created_collection, name)

    @pytest.mark.parametrize("db_name, collection_name, expression, no_of_index", [
        (random_string(6), random_string(6), random_string(6), 1),
        (random_string(6), random_string(6), random_string(6), 9),
        (random_string(6), random_string(6), random_string(6), 99),
    ])
    def test_getIndexNames(self, db_name, collection_name, expression, no_of_index):
        db = self.db_obj.create(db_name)
        scopeName = "_default"
        created_collection = self.db_obj.createCollection(db, collection_name, scopeName)
        created_index = []
        for i in range(0, no_of_index):
            created_index.append('index-' + str(i))
            self.collection_obj.createValueIndex(created_collection, 'index-' + str(i), expression)
        retrived_index = self.collection_obj.getIndexNames(created_collection)
        assert sorted(retrived_index) == sorted(created_index)
        
