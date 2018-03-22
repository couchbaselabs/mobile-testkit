import pytest
from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestDatabase(object):

    @pytest.mark.parametrize("db_name, err_msg", [
        ("", "name should not be empty"),
        (random_string(1028), "File name too long")
    ])
    def test_database_create_exception(self, db_name, err_msg):
        '''
        @summary: Checking for the Exception handling in database create API
        '''
        if self.liteserv_platform != "android" and db_name == "":
            pytest.skip("Test not applicable for ios")

        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        try:
            self.db_obj.create(db_name)
            assert 0
        except Exception, err_resp:
            assert err_msg in str(err_resp)

    def test_getDocument_exception(self):
        if self.liteserv_platform == "ios":
            pytest.skip("Test not applicable for ios")

        db = self.db_obj.create(random_string(6))
        # checking when Null/None documentId is provided
        err_msg = "a documentID parameter is null"
        try:
            self.db_obj.getDocument(db, None)
            assert 0
        except Exception, err_resp:
            assert err_msg in str(err_resp)
        # checking document in db with empty name
        doc_id = self.db_obj.getDocument(db, "")
        assert doc_id == -1
        # checking for a non-existing doc in DB
        doc_id = self.db_obj.getDocument(db, "I-do-not-exist")
        assert doc_id == -1

    def test_saveDocument_exception(self):
        if self.liteserv_platform == "ios":
            pytest.skip("Test not applicable for ios")

        db = self.db_obj.create(random_string(6))
        err_msg = "a document parameter is null"
        try:
            self.db_obj.saveDocument(db, None)
            assert 0
        except Exception, err_resp:
            assert err_msg in str(err_resp)

    def test_delete_exception(self):
        if self.liteserv_platform == "ios":
            pytest.skip("Test not applicable for ios")

        db = self.db_obj.create(random_string(6))
        # Exception checking when document id is null
        err_msg = "a document parameter is null"
        try:
            self.db_obj.delete(database=db, document=None)
            assert 0
        except Exception, err_resp:
            assert err_msg in str(err_resp)
        try:
            self.db_obj.purge(database=db, document=None)
            assert 0
        except Exception, err_resp:
            assert err_msg in str(err_resp)

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).capitalize(),
        random_string(6).upper(),
    ])
    def test_database_create(self, db_name):
        '''
        @summary: Testing Database constructor method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        assert self.db_obj.getName(db) == db_name
        assert self.db_obj.deleteDB(db) == -1

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).capitalize(),
        random_string(6).upper(),
    ])
    def test_database_close(self, db_name):
        '''
        @summary: Testing close method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        assert self.db_obj.close(db) == -1

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
    def test_deleteDB(self, db_name):
        '''
        @summary: Testing delete(DB) method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        path = self.db_obj.getPath(db)
        assert self.db_obj.deleteDB(db) == -1
        assert self.db_obj.exists(db_name, path) is False

    @pytest.mark.parametrize("db_name, doc_id", [
        (random_string(1), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(128), random_string(6)),
        ("_{}".format(random_string(6)), random_string(6)),
        ("{}_".format(random_string(6)), random_string(6)),
        ("_{}_".format(random_string(6)), random_string(6)),
        (random_string(6, digit=True), random_string(6)),
        (random_string(6).capitalize(), random_string(6)),
        (random_string(6).upper(), random_string(6))
    ])
    def test_delete_doc(self, db_name, doc_id):
        '''
        @summary: Testing delete method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db_name = db_name.lower()
        db = self.db_obj.create(db_name)
        assert self.db_obj.getDocument(db, doc_id) == -1

        doc = self.doc_obj.create(doc_id=doc_id)
        doc = self.doc_obj.setString(doc, "key", "value")
        self.db_obj.saveDocument(db, doc)
        doc_res = self.db_obj.getDocument(db, doc_id)
        assert doc_res is not None
        assert self.doc_obj.getId(doc_res) == doc_id
        assert self.db_obj.getCount(db) == 1
        assert self.doc_obj.getString(doc_res, "key") == "value"

        self.db_obj.delete(document=doc, database=db)
        doc_res = self.db_obj.getDocument(db, doc_id)
        assert self.db_obj.getCount(db) == 0
        doc_res = self.db_obj.getDocument(db, doc_id)
        assert doc_res == -1
        assert self.db_obj.deleteDB(db) == -1

    @pytest.mark.parametrize("db_name, doc_id, num_of_docs", [
        (random_string(6), random_string(8), 9),
        (random_string(6), random_string(8), 99),
        (random_string(6), random_string(8), 999),
        (random_string(6), random_string(8), 9999)
    ])
    def test_getCount(self, num_of_docs, db_name, doc_id):
        '''
        @summary: Testing getCount method of Database API
        '''
        db = self.db_obj.create(db_name)
        for i in range(num_of_docs):
            doc = self.doc_obj.create(doc_id="{}_{}".format(doc_id, i))
            self.db_obj.saveDocument(db, doc)
        doc_count = self.db_obj.getCount(db)
        assert num_of_docs == doc_count
        assert self.db_obj.deleteDB(db) == -1

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
    def test_exists(self, db_name):
        '''
        @summary: Testing exist method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        path = self.db_obj.getPath(db)
#         directory = "/".join(path.split("/")[:-2])
        assert self.db_obj.exists(db_name, path)
        assert self.db_obj.deleteDB(db) == -1
        assert not self.db_obj.exists(db_name, path)

    @pytest.mark.parametrize("db_name, doc_id", [
        # "",
        (random_string(1), random_string(6)),
        (random_string(6), random_string(6)),
        # (random_string(128), random_string(6)),
        ("_{}".format(random_string(6)), random_string(6)),
        ("{}_".format(random_string(6)), random_string(6)),
        ("_{}_".format(random_string(6)), random_string(6)),
        (random_string(6, digit=True), random_string(6)),
        (random_string(6).capitalize(), random_string(6)),
        (random_string(6).upper(), random_string(6))
    ])
    def test_getDocument(self, db_name, doc_id):
        '''
        @summary: Testing getDocument method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        doc = self.doc_obj.create(doc_id)
        self.db_obj.saveDocument(db, doc)
        new_doc = self.db_obj.getDocument(db, doc_id)
        assert self.doc_obj.getId(new_doc) == self.doc_obj.getId(doc)
        assert self.db_obj.deleteDB(db) == -1

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).capitalize(),
        random_string(6).upper(),
    ])
    def test_getName(self, db_name):
        '''
        @summary: Testing getName method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        assert db_name == str(self.db_obj.getName(db))
        assert self.db_obj.deleteDB(db) == -1

    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).capitalize(),
        random_string(6).upper(),
    ])
    def test_getPath(self, db_name):
        '''
        @summary: Testing getPath method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        db = self.db_obj.create(db_name)
        assert self.db_obj.getPath(db)
        assert self.db_obj.deleteDB(db) == -1

    @pytest.mark.parametrize("db1, db2, doc_id", [
        # "",
        (random_string(1), random_string(1), random_string(6)),
        (random_string(6), random_string(6), random_string(6)),
        # (random_string(128), random_string(128), random_string(6)),
        ("_{}".format(random_string(6)), "_{}".format(random_string(6)), random_string(6)),
        ("{}_".format(random_string(6)), "{}_".format(random_string(6)), random_string(6)),
        ("_{}_".format(random_string(6)), "_{}_".format(random_string(6)), random_string(6)),
        (random_string(6, digit=True), random_string(6, digit=True), random_string(6)),
        (random_string(6).capitalize(), random_string(6).capitalize(), random_string(6)),
        (random_string(6).upper(), random_string(6).upper(), random_string(6))
    ])
    def test_purge(self, db1, db2, doc_id):
        '''
        @summary: Testing purge method of Database API
        '''
        doc_id_prefix = "bar"
        doc = self.doc_obj.create(doc_id=doc_id_prefix)
        db_1 = self.db_obj.create(db1)
        db_2 = self.db_obj.create(db2)
        self.db_obj.saveDocument(db_1, doc)
        self.db_obj.saveDocument(db_2, doc)
        self.db_obj.purge(document=doc, database=db_1)
        assert self.db_obj.getDocument(db_2, doc_id) == -1
        assert self.db_obj.getDocument(db_2, doc_id)
        assert self.db_obj.deleteDB(db_1) == -1
        assert self.db_obj.deleteDB(db_2) == -1

    @pytest.mark.parametrize("db_name, doc_id", [
        (random_string(1), random_string(6)),
        (random_string(6), random_string(6)),
        (random_string(128), random_string(6)),
        ("_{}".format(random_string(6)), random_string(6)),
        ("{}_".format(random_string(6)), random_string(6)),
        ("_{}_".format(random_string(6)), random_string(6)),
        (random_string(6, digit=True), random_string(6)),
        (random_string(6).capitalize(), random_string(6)),
        (random_string(6).upper(), random_string(6))
    ])
    def test_saveDocument(self, db_name, doc_id):
        '''
        @summary: Testing save method of Database API
        '''
        if len(db_name) >= 128 and (self.liteserv_platform != "ios" or self.liteserv_platform != "android"):
            pytest.skip("Test not supported on .net platfomrs")

        doc = self.doc_obj.create(doc_id)
        db = self.db_obj.create(db_name)
        doc_in_db_check = self.db_obj.getDocument(db, doc_id)
        assert doc_in_db_check == -1
        self.db_obj.saveDocument(db, doc)
        doc_res = self.db_obj.getDocument(db, doc_id)
        assert doc_id == str(self.doc_obj.getId(doc_res))
        assert self.db_obj.deleteDB(db) == -1

    def test_getDocuments(self):
        '''
        @summary: Testing the bulk add and bulk get docs. This also
        test inbatch API of Database class.
        '''
        doc_id_prefix = "bar"
        num_of_docs = 5
        db = self.db_obj.create("db_name")
        documents = dict()
        ids = []
        for i in range(num_of_docs):
            data = {}
            doc_id = "{}_{}".format(doc_id_prefix, i)
            ids.append(doc_id)
            data["test_string_{}".format(i)] = "value_{}".format(i)
            documents[doc_id] = data
        self.db_obj.saveDocuments(db, documents)
        docs_in_db = self.db_obj.getDocuments(db, ids)
        assert num_of_docs == self.db_obj.getCount(db)
        assert documents == docs_in_db
        assert self.db_obj.deleteDB(db) == -1
