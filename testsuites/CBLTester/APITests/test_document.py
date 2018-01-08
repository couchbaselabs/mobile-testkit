import random
import pytest

from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestDocument(object):

    @pytest.mark.parametrize("doc_id1, doc_id2", [
        (random_string(1), random_string(1)),
        (random_string(6), random_string(6)),
        ("_{}".format(random_string(6)), "_{}".format(random_string(6))),
        ("{}_".format(random_string(6)), "_{}".format(random_string(6))),
        ("_{}_".format(random_string(6)), "_{}".format(random_string(6))),
        (random_string(6).capitalize(), random_string(6).capitalize()),
        (random_string(6).upper(), random_string(6).upper()),
        (random_string(8, digit=True), random_string(8, digit=True)),
        (random_string(128), random_string(128)),
    ])
    def test_document(self, doc_id1, doc_id2):
        '''
        @summary: Testing Document Constructor
        '''
        doc_1 = self.doc_obj.create()
        assert self.doc_obj.getId(doc_1)

        doc_2 = self.doc_obj.create(doc_id1)
        assert doc_id1 == self.doc_obj.getId(doc_2)

        doc_dict = {"test1": "test_string"}
        doc_3 = self.doc_obj.create(dictionary=doc_dict)
        assert self.doc_obj.getId(doc_3)

        doc_4 = self.doc_obj.create(doc_id2, doc_dict)
        assert doc_id2 == self.doc_obj.getId(doc_4)

    @pytest.mark.parametrize("key, value", [
        (random_string(5), ""),
        (random_string(5), random_string(1)),
        (random_string(5), random_string(10)),
        (random_string(5), "_{}".format(random_string(5))),
        (random_string(5), "{}_".format(random_string(8))),
        (random_string(5), "_{}_".format(random_string(9))),
        (random_string(5), random_string(9).capitalize()),
        (random_string(5), random_string(9).upper()),
        (random_string(5), "{}12".format(random_string(5))),
        (random_string(5), random_string(10, digit=True))
    ])
    def test_contains(self, key, value):
        '''
        @summary: Testing Document set/contains method
        '''
        if self.liteserv_platform == "ios" and value == "":
            pytest.skip("Test not applicable for ios")

        doc = self.doc_obj.create()
        self.doc_obj.setString(doc, key, value)
        assert self.doc_obj.contains(doc, key)

    @pytest.mark.parametrize("num_of_keys", [
        9,
        99,
        999,
        9999
    ])
    def test_count(self, num_of_keys):
        '''
        @summary: Testing Document count method
        '''
        doc = self.doc_obj.create()
        assert self.doc_obj.count(doc) == 0
        for i in range(num_of_keys):
            key = "test_{}".format(i)
            value = "Test content - {}".format(i)
            self.doc_obj.setString(doc, key, value)
        assert self.doc_obj.count(doc) == num_of_keys

    def test_remove(self):
        '''
        @summary: Testing Document remove method
        '''
        key = "test"
        value = "test-1"
        doc = self.doc_obj.create()
        self.doc_obj.setString(doc, key, value)
        assert self.doc_obj.contains(doc, "test")
        self.doc_obj.remove(doc, "test")
        assert not self.doc_obj.contains(doc, "test")

    def test_toMap(self):
        '''
        @summary: Testing Document toMap method
        '''
        doc = self.doc_obj.create()

        #checking get and sets for String
        hashmap = {}
        key = "string_key"
        value = "Test String"
        hashmap[key] = value
        self.doc_obj.setString(doc, key, value)
        key = "Integer_key"
        value = 1
        hashmap[key] = value
        self.doc_obj.setInt(doc, key, value)
        key = "Long_key"
        value = long(random.randint(10, 10000))
        hashmap[key] = value
        self.doc_obj.setLong(doc, key, value)
        key = "Float_key"
        value = 3.0
        hashmap[key] = value
        self.doc_obj.setFloat(doc, key, value)
        result_map = self.doc_obj.toMap(doc)
        assert hashmap == result_map

    def test_getKeys(self):
        '''
        @summary: Testing Document getKeys method
        '''
        doc = self.doc_obj.create()

        #checking for empty doc
        assert self.doc_obj.getKeys(doc) == []
        result_list = []
        key = "string_key"
        value = "Test String"
        result_list.append(key)
        self.doc_obj.setString(doc, key, value)
        key = "Integer_key"
        value = 1
        result_list.append(key)
        self.doc_obj.setInt(doc, key, value)
        key = "Long_key"
        value = long(random.randint(10, 10000))
        result_list.append(key)
        self.doc_obj.setLong(doc, key, value)
        key = "Float_key"
        value = random.uniform(1, 10)
        result_list.append(key)
        self.doc_obj.setFloat(doc, key, value)
        result_list.sort()
        assert sorted(self.doc_obj.getKeys(doc)) == result_list

    @pytest.mark.parametrize("key, value", [
        (random_string(5), ""),
        (random_string(5), random_string(1)),
        (random_string(5), random_string(10)),
        (random_string(5), "_{}".format(random_string(5))),
        (random_string(5), "{}_".format(random_string(8))),
        (random_string(5), "_{}_".format(random_string(9))),
        (random_string(5), random_string(9).capitalize()),
        (random_string(5), random_string(9).upper()),
        (random_string(5), "{}12".format(random_string(5))),
        (random_string(5), random_string(10, digit=True)),
        (random_string(128), random_string(128))
    ])
    def test_get_set_string(self, key, value):
        '''
        @summary: Testing Get and Set String method of Document API
        '''
        if self.liteserv_platform == "ios" and value == "":
            pytest.skip("Test not applicable for ios")

        doc = self.doc_obj.create()
        self.doc_obj.setString(doc, key, value)
        assert value == self.doc_obj.getString(doc, key)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), random.randint(0, 9)),
        (random_string(6), random.randint(10, 99)),
        (random_string(6), random.randint(100, 999)),
        (random_string(6), random.randint(1000, 9999))
    ])
    def test_get_set_integer(self, key, value):
        '''
        @summary: Testing Get and Set Integer method of Document API
        '''
        doc = self.doc_obj.create()
        self.doc_obj.setInt(doc, key, value)
        assert value == self.doc_obj.getInt(doc, key)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), True),
        (random_string(6), False)
    ])
    def test_get_set_boolean(self, key, value):
        '''
        @summary: Testing Get and Set Boolean method of Document API
        '''
        doc = self.doc_obj.create()
        self.doc_obj.setBoolean(doc, key, value)
        assert value == self.doc_obj.getBoolean(doc, key)

    def test_get_set_dictionary(self):
        '''
        @summary: Testing Get and Set Dictionary method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Dictionary_key"
        value = self.dict_obj.create()
        self.dict_obj.setString(value, "String_key", random_string(12))
        self.dict_obj.setInt(value, "Integer_key", random.randint(0, 50))
        self.doc_obj.setDictionary(doc, key, value)
        result_dict = self.doc_obj.getDictionary(doc, key)
        assert self.dict_obj.contains(result_dict, "String_key")
        assert self.dict_obj.contains(result_dict, "Integer_key")

    def test_get_set_date(self):
        '''
        @summary: Testing Get and Set Date method of Document API
        '''
        doc = self.doc_obj.create()
        key = "Date_key"
        date_obj = self.datatype.setDate()
        self.doc_obj.setDate(doc, key, date_obj)
        new_date = self.doc_obj.getDate(doc, key)
        assert self.datatype.compareDate(date_obj, new_date)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), "{}".format(random.uniform(0, 1))),
        (random_string(6), "{}".format(random.uniform(1, 10))),
        (random_string(6), "{}".format(random.uniform(11, 100))),
        (random_string(6), "{}".format(random.uniform(101, 1000)))
    ])
    def test_get_set_double(self, key, value):
        '''
        @summary: Testing Get and Set Double method of Document API
        '''
        doc = self.doc_obj.create()
        double_obj = self.datatype.setDouble(value)
        self.doc_obj.setDouble(doc, key, double_obj)
        assert self.datatype.compareDouble(double_obj, self.doc_obj.getDouble(doc, key))

    @pytest.mark.parametrize("key, value", [
        (random_string(6), round(random.uniform(0, 1), 3)),
        (random_string(6), round(random.uniform(1, 10), 3)),
        (random_string(6), round(random.uniform(11, 100), 3)),
        (random_string(6), round(random.uniform(101, 1000), 3))
    ])
    def test_get_set_float(self, key, value):
        '''
        @summary: Testing Get and Set Float method of Document API
        '''
        doc = self.doc_obj.create()
#       float_obj = self.datatype.setFloat(value)
        self.doc_obj.setFloat(doc, key, value)
        result = self.doc_obj.getFloat(doc, key)
        assert value == result

    @pytest.mark.parametrize("key, value", [
        (random_string(6), "{}".format(random.randint(0, 9))),
        (random_string(6), "{}".format(random.randint(10, 99))),
        (random_string(6), "{}".format(random.randint(100, 999))),
        (random_string(6), "{}".format(random.randint(1000, 9999)))
    ])
    def test_get_set_long(self, key, value):
        '''
        @summary: Testing Get and Set Float method of Document API
        '''
        doc = self.doc_obj.create()
        long_obj = self.datatype.setLong(value)
        self.doc_obj.setLong(doc, key, long_obj)
        result = self.doc_obj.getLong(doc, key)
        assert self.datatype.compareLong(long_obj, result)
