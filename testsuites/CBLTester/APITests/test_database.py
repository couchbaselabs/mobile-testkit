'''
Created on 23-Nov-2017

@author: hemant
'''
import unittest
from time import sleep

from CBLClient.Database import Database
from CBLClient.Document import Document

baseUrl = "http://172.16.1.154:8080"
dbName = "foo"
docIdPrefix = "bar"

class TestDatabase(unittest.TestCase):
    def test_database(self):
        '''
        @summary: Testing Database constructor
        '''
        db = Database(baseUrl);
        db_obj = db.create(dbName) 
        self.assertTrue(db.getName(db_obj) == "foo", "Database Create Failed")
    
    
    def test_database_add_listener(self):
        '''
        @summary: Checking if we are able to add datbase or document 
        listener to Database object
        '''
        self.assertTrue(True, "Not Implemented")

    def test_database_close(self):
        '''
        @summary: Testing Database constructor
        '''
        #base_url = setup_client_syncgateway_test["base_url"]
        db = Database(baseUrl);
        #doc = Document(baseUrl)
        #doc_obj = doc.create(id=docPrefix)
        db_obj = db.create(dbName) 
        self.assertEqual(-1, db.close(db_obj), "Database Close Failed")
        #self.assertEqual("ERROR", db.save(db_obj, doc_obj), "Database Close Failed")

    def test_compact(self):
        self.assertTrue(True, "Not Implemented")

    def test_contains(self):
        '''
        @summary: Testing Database contains 
        '''
        db = Database(baseUrl);
        doc = Document(baseUrl)
        doc_obj = doc.create(doc_id=docIdPrefix)
        db_obj = db.create(dbName)
        db.save(db_obj, doc_obj)
        self.assertTrue(db.contains(db_obj, docIdPrefix),
                        "Document is not available in Database")

    def test_deleteDB(self):
        '''
        @summary: Testing Delete for Database
        '''
        db = Database(baseUrl);
        db_obj = db.create(dbName)
        #sleep(5)
        out = db.deleteDB(db_obj)
        self.assertEqual(-1, out, "Database Delete failed")

    def test_delete(self):
        '''
        @summary: Testing Delete a document from Database
        '''
        db = Database(baseUrl);
        doc = Document(baseUrl)
        doc_obj = doc.create(doc_id=docIdPrefix)
        db_obj = db.create(dbName)
        db.save(db_obj, doc_obj)
        db.delete(document=doc_obj, database=db_obj)
        doc_res = db.getDocument(db_obj, docIdPrefix)
        self.assertEqual(None, doc_res , "Document delete failed")

    def test_getCount(self):
        '''
        @summary: Testing getCount on documents in Database
        '''
        num_doc = 10
        db = Database(baseUrl);
        doc = Document(baseUrl)
        db_obj = db.create(dbName)
        for i in range(num_doc):
            doc_obj = doc.create(doc_id="{}_{}".format(docIdPrefix, i))
            db.save(db_obj, doc_obj)
        doc_count = db.getCount(db_obj)
        self.assertEqual(num_doc, doc_count, "Database getCount failed")

    def test_exists(self):
        '''
        @summary: Test exist method to check if database with given name
        exists.
        '''
        self.assertTrue(True, "Not Implemented")

    def test_getDocument(self):
        db = Database(baseUrl);
        doc = Document(baseUrl)
        db_obj = db.create(dbName)
        doc_obj = doc.create(docIdPrefix)
        new_doc_obj = db.getDocument(db_obj, docIdPrefix)
        self.assertEqual(doc.getId(new_doc_obj), doc.getId(doc_obj),
                         "Database getDocument failed")

    def test_getName(self):
        db = Database(baseUrl);
        db_obj = db.create(dbName)
        self.assertEqual(dbName, db.getName(db_obj),
                         "Database getName failed.")

    def test_getPath(self):
        db = Database(baseUrl);
        db_obj = db.create(dbName)
        self.assertIsNotNone(db.getPath(db_obj),
                             "Database getPath failed")

    def test_purge(self):
        db = Database(baseUrl);
        doc = Document(baseUrl)
        doc_obj= doc.create(doc_id=docIdPrefix)
        db_obj_1 = db.create("{}_1".format(dbName))
        db_obj_2 = db.create("{}_2".format(dbName))
        db.save(db_obj_1, doc_obj)
        db.save(db_obj_2, doc_obj)
        db.purge(document=doc_obj, database=db_obj_1)
        self.assertIsNone(db.getDocument(db_obj_1, docIdPrefix),
                          "Document purge failed")
        self.assertIsNotNone(db.getDocument(db_obj_2, docIdPrefix),
                             "Document purge failed")

    def test_save(self):
        db = Database(baseUrl);
        #doc = Document(baseUrl)
        #doc_obj= doc.create(doc_id=docIdPrefix)
        db_obj = db.create(dbName)
        doc_in_db_check = db.getDocument(db_obj, docIdPrefix)
        self.assertIsNone(doc_in_db_check,
                          "Database save method failed")
        #db.save(db_obj, doc_obj)
        #doc_res = db.getDocument(db_obj, docIdPrefix)
        #self.assertEqual(docIdPrefix,doc.getId(doc_res),
        #                  "Database save method failed")

if __name__ == '__main__':
    unittest.main()
