import unittest

from CBLClient.Document import Document
from CBLClient.Dictionary import Dictionary
from CBLClient.DataTypeInitiator import DataTypeInitiator

#baseUrl = "http://172.16.1.154:8080"
baseUrl = "http://192.168.0.113:8080"
dbName = "foo"
docIdPrefix = "bar"

class TestDocument(unittest.TestCase):

    doc_obj = Document(baseUrl)
    dict_obj = Dictionary(baseUrl)
    datatype = DataTypeInitiator(baseUrl)
    def test_document(self):
        '''
        @summary: Testing Document Constructor
        '''
        doc_1 = self.doc_obj.create()
        self.assertIsNotNone(self.doc_obj.getId(doc_1),
                             "Document create with random UUID failed")
        doc_2 = self.doc_obj.create(docIdPrefix + "_1")
        self.assertEqual(docIdPrefix + "_1", self.doc_obj.getId(doc_2),
                         "Document create with user defined Id failed")
        datatype = DataTypeInitiator(baseUrl)
        doc_dict = datatype.hashMap()
        doc_3 = self.doc_obj.create(dictionary=doc_dict)
        self.assertIsNotNone(self.doc_obj.getId(doc_3),
                             "Document create with dictionary failed")
        doc_4 = self.doc_obj.create(docIdPrefix + "_2", doc_dict)
        self.assertEqual(docIdPrefix + "_2", self.doc_obj.getId(doc_4),
                         "Document create with user defined Id and "\
                         "dictionary failed")

    def test_contains(self):
        '''
        @summary: Testing Document set/contains method
        '''
        content_dict = self.datatype.hashMap()
        self.datatype.put(content_dict, "test", "test-1")
        doc = self.doc_obj.create()
        doc = self.doc_obj.set(doc, content_dict)
        self.assertTrue(self.doc_obj.contains(doc, "test"),
                        "Document set method failed")

    def test_count(self):
        '''
        @summary: Testing Document count method
        '''
        content_dict = self.datatype.hashMap()
        self.datatype.put(content_dict, "test", "test-1")
        doc = self.doc_obj.create()
        self.assertEqual(0, self.doc_obj.count(doc), "Document count failed")
        doc = self.doc_obj.set(doc, content_dict)
        self.assertEqual(1, self.doc_obj.count(doc), "Document count failed")

    def test_remove(self):
        '''
        @summary: Testing Document remove method
        '''
        content_dict = self.datatype.hashMap()
        self.datatype.put(content_dict, "test", "test-1")
        doc = self.doc_obj.create()
        doc = self.doc_obj.set(doc, content_dict)
        self.assertTrue(self.doc_obj.contains(doc, "test"),
                        "Document set method failed")
        self.doc_obj.remove(doc, "test")
        self.assertFalse(self.doc_obj.contains(doc, "test"),
                        "Document set method failed")


    def test_gets_sets_string(self):
        '''
        @summary: Testing Gets and Sets String method of Document API
        '''
        doc = self.doc_obj.create()

        #checking get and sets for String
        key = "string_key"
        value = "Test String"
        self.doc_obj.setString(doc, key, value)
        self.assertEqual(value, self.doc_obj.getString(doc, key),
                         "Document setString and getString failed")

    def test_gets_sets_integer(self):
        '''
        @summary: Testing Gets and Sets Integer method of Document API
        '''

        doc = self.doc_obj.create()
        key = "Integer_key"
        value = 123
        self.doc_obj.setInt(doc, key, value)
        self.assertEqual(value, self.doc_obj.getInt(doc, key),
                         "Document setInt and getInt failed")

    def test_gets_sets_boolean(self):
        '''
        @summary: Testing Gets and Sets Boolean method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Boolean_key"
        value = True
        self.doc_obj.setBoolean(doc, key, value)
        self.assertTrue(self.doc_obj.getBoolean(doc, key),
                         "Document setBoolean and getBoolean failed")

    def test_gets_sets_dictionary(self):
        '''
        @summary: Testing Gets and Sets Dictionary method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Dictionary_key"
        value = self.dict_obj.create()
        self.dict_obj.setString(value, "test_key", "dict_value")
        self.doc_obj.setDictionary(doc, key, value)
        result_dict = self.doc_obj.getDictionary(doc, key)
        self.assertEqual("dict_value", self.dict_obj.getString(result_dict,
                                                          "test_key"),
                         "Document setDictionary and getDictionary failed")

    def test_gets_sets_date(self):
        '''
        @summary: Testing Gets and Sets Date method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Date_key"
        date_obj = self.datatype.setDate()
        self.doc_obj.setDate(doc, key, date_obj)
        new_date = self.doc_obj.getDate(doc, key)
        self.assertTrue(self.datatype.compare(date_obj, new_date))
        #self.assertIsNotNone(new_date,
        #                     "Document getDate and setDate failed")

    def test_gets_sets_double(self):
        '''
        @summary: Testing Gets and Sets Double method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Double_key"
        value = '2.0'
        double_obj = self.datatype.setDouble(value)
        self.doc_obj.setDouble(doc, key, double_obj)
        self.assertTrue(self.datatype.compare(double_obj,
                                         self.doc_obj.getDouble(doc, key)),
                        "Document getDouble and setDouble failed")

    def test_gets_sets_float(self):
        '''
        @summary: Testing Gets and Sets Float method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Float_key"
        value = '2.0'
        float_obj = self.datatype.setFloat(value)
        self.doc_obj.setFloat(doc, key, float_obj)
        result = self.doc_obj.getFloat(doc, key)
        self.assertTrue(self.datatype.compare(float_obj, result),
                        "Document getFloat and setFloat failed")

    def test_gets_sets_long(self):
        '''
        @summary: Testing Gets and Sets Float method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Long_key"
        value = '2'
        long_obj = self.datatype.setFloat(value)
        self.doc_obj.setFloat(doc, key, long_obj)
        result = self.doc_obj.getFloat(doc, key)
        self.assertTrue(self.datatype.compare(long_obj, result),
                        "Document getLong and setLong failed")