import unittest

from CBLClient.Document import Document
from CBLClient.Dictionary import Dictionary

baseUrl = "http://172.16.1.154:8080"
dbName = "foo"
docIdPrefix = "bar"

class TestDocument(unittest.TestCase):

    def test_document(self):
        doc = Document(baseUrl)
        doc_1 = doc.create()
        self.assertIsNotNone(doc.getId(doc_1),
                             "Document create with random UUID failed")
        doc_2 = doc.create(docIdPrefix + "_1")
        self.assertEqual(docIdPrefix + "_1", doc.getId(doc_2),
                         "Document create with user defined Id failed")
        dict_obj = Dictionary(baseUrl)
        doc_dict = dict_obj.create()
        doc_3 = doc.create(dictionary=doc_dict)
        self.assertIsNotNone(doc.getId(doc_3),
                             "Document create with dictionary failed")
        doc_4 = doc.create(docIdPrefix + "_2", doc_dict)
        self.assertEqual(docIdPrefix + "_2", doc.getId(doc_4),
                         "Document create with user defined Id and "\
                         "dictionary failed")

    def test_set(self):
        dict_obj = Dictionary(baseUrl)
        doc_obj = Document(baseUrl)
        content_dict = dict_obj.create()
        dict_obj.put(content_dict, "test", "test-1")
        doc = doc_obj.create()
        doc = doc_obj.set(doc, content_dict)
        self.assertTrue(doc_obj.contains(doc, "test"),
                        "Document set method failed")
