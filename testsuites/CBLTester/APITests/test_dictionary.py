import random
import pytest

from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestDictionary(object):

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
    def test_create(self, key, value):
        '''
        @summary: Testing create method of Dictionary API
        '''
        if self.liteserv_platform == "ios" and value == "":
            pytest.skip("Test not applicable for ios")

        content_dict = self.dict_obj.create()
        self.dict_obj.setString(content_dict, key, value)
        assert self.dict_obj.getString(content_dict, key) == value

        hashmap = {}
        hashmap[key] = value
        content_dict_2 = self.dict_obj.create(hashmap)
        assert self.dict_obj.getString(content_dict_2, key) == value

    @pytest.mark.parametrize("key, value", [
        (random_string(5), random.uniform(1, 10)),
        (random_string(5), random.random()),
        (random_string(5), random.randint(1, 1000)),
        (random_string(5), random.randint(100000, 10000000)),
        (random_string(5), random_string(6))
    ])
    def test_contains(self, key, value):
        '''
        @summary: Testing contains method of Dictionary API
        '''
        test_dict = self.dict_obj.create()
        self.dict_obj.setString(test_dict, key, value)
        assert self.dict_obj.contains(test_dict, key)

    @pytest.mark.parametrize("num_of_keys", [
        9,
        99,
        999,
        9999
    ])
    def test_count(self, num_of_keys):
        '''
        @summary: Testing count method of Dictionary API
        '''
        hashmap = {}
        key = "string_key"
        value = "Test String"
        for i in range(num_of_keys):
            hashmap["{}_{}".format(key, i)] = value
        content_dict = self.dict_obj.create(hashmap)
        assert num_of_keys == self.dict_obj.count(content_dict)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), True),
        # (random_string(6), False) #TODO ios panics
    ])
    def test_get_set_boolean(self, key, value):
        '''
        @summary: Testing get and set Boolean methods of Dictionary API
        '''
        content_dict = self.dict_obj.create()
        self.dict_obj.setBoolean(content_dict, key, value)
        assert self.dict_obj.getBoolean(content_dict, key) == value

    def test_get_set_date(self):
        '''
        @summary: Testing get and set Date methods of Dictionary API
        '''
        # TODO implementation does not work on ios
        key = "Date_key"
        value = self.datatype.setDate()
        content_dict = self.dict_obj.create()
        self.dict_obj.setDate(content_dict, key, value)
        # assert self.datatype.compare(value,
        #                            self.dict_obj.getDate(content_dict,
        #                                                   key))
        assert self.datatype.compareDate(value, self.dict_obj.getDate(content_dict, key))

    def test_get_set_dictionary(self):
        '''
        @summary: Testing get and set Dictionary methods of Dictionary API
        '''
        # TODO ios gets back {} for self.datatype.hashMap()
        hashmap = {}
        key = "Date_key"
        value = self.datatype.setDate()
        hashmap[key] = value
        key = "Double_key"
        value = self.datatype.setDouble(2.0)
        hashmap[key] = value
        key = "Float_key"
        value = self.datatype.setFloat(3.0)
        hashmap[key] = value
        key = "Integer_key"
        value = 4
        hashmap[key] = value
        key = "Long_key"
        value = self.datatype.setLong(1234567890)
        hashmap[key] = value
        key = "String_key"
        value = "Test String"
        hashmap[key] = value
        content = self.dict_obj.create(hashmap)
        content_dict = self.dict_obj.create()
        self.dict_obj.setDictionary(content_dict, "hashmap", content)
        content_check = self.dict_obj.getDictionary(content_dict, "hashmap")
        for key in hashmap:
            assert self.dict_obj.contains(content_check, key)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), "{}".format(random.uniform(0, 1))),
        (random_string(6), "{}".format(random.uniform(1, 10))),
        (random_string(6), "{}".format(random.uniform(11, 100))),
        (random_string(6), "{}".format(random.uniform(101, 1000)))
    ])
    def test_get_set_double(self, key, value):
        '''
        @summary: Testing get and set Double methods of Dictionary API
        '''
        # TODO implementation does not work on ios
        double_value = self.datatype.setDouble(float(value))
        content_dict = self.dict_obj.create()
        self.dict_obj.setDouble(content_dict, key, double_value)
        # assert self.datatype.compare(double_value,
        #                              self.dict_obj.getDouble(
        #                                  content_dict, key))
        assert self.datatype.compareDouble(double_value, self.dict_obj.getDouble(content_dict, key))

    @pytest.mark.parametrize("key, value", [
        (random_string(6), round(random.uniform(0, 1), 4)),
        (random_string(6), round(random.uniform(1, 10), 4)),
        (random_string(6), round(random.uniform(11, 100), 4)),
        (random_string(6), round(random.uniform(101, 1000), 4))
    ])
    def test_get_set_float(self, key, value):
        '''
        @summary: Testing get and set Float methods of Dictionary API
        '''
        # TODO Precision issue with ios assert 978.5709 == 978.571
        content_dict = self.dict_obj.create()
        self.dict_obj.setFloat(content_dict, key, value)
        assert value == self.dict_obj.getFloat(content_dict, key)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), random.randint(0, 9)),
        (random_string(6), random.randint(10, 99)),
        (random_string(6), random.randint(100, 999)),
        (random_string(6), random.randint(1000, 9999))
    ])
    def test_get_set_int(self, key, value):
        '''
        @summary: Testing get and set Integer methods of Dictionary API
        '''
        content_dict = self.dict_obj.create()
        self.dict_obj.setInt(content_dict, key, value)
        assert value == self.dict_obj.getInt(content_dict, key)

    @pytest.mark.parametrize("key, value", [
        (random_string(6), "{}".format(random.randint(0, 1))),
        (random_string(6), "{}".format(random.randint(1, 10))),
        (random_string(6), "{}".format(random.randint(11, 100))),
        (random_string(6), "{}".format(random.randint(101, 1000)))
    ])
    def test_get_set_long(self, key, value):
        '''
        @summary: Testing get and set Long methods of Dictionary API
        '''
        if self.liteserv_platform == "ios":
            pytest.skip("Test not applicable for ios")

        long_value = self.datatype.setLong(value)
        content_dict = self.dict_obj.create()
        self.dict_obj.setLong(content_dict, key, long_value)
        assert self.datatype.compare(long_value,
                                     self.dict_obj.getLong(content_dict,
                                                           key))

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
        # (random_string(128), random_string(128, True)),
    ])
    def test_get_set_string(self, key, value):
        '''
        @summary: Testing get and set String methods of Dictionary API
        '''
        content_dict = self.dict_obj.create()
        self.dict_obj.setString(content_dict, key, value)
        assert value == self.dict_obj.getString(content_dict, key)

    @pytest.mark.parametrize("key, value, num_of_keys", [
        (random_string(5), random_string(5), 9),
        (random_string(5), random_string(5), 99),
        # (random_string(5), random_string(5), 999),
        # (random_string(5), random_string(5), 9999)
    ])
    def test_getKeys(self, key, value, num_of_keys):
        '''
        @summary: Testing getKeys methods of Dictionary API
        '''
        hashmap = {}
        keys_list = []
        for i in range(num_of_keys):
            keys_list.append("{}_{}".format(key, i))
            hashmap["{}_{}".format(key, i)] = value
        content_dict = self.dict_obj.create(hashmap)
        keys_list.sort()
        assert sorted(self.dict_obj.getKeys(content_dict)) == keys_list

    @pytest.mark.parametrize("key, value", [
        (random_string(5), random.uniform(1, 10)),
        (random_string(5), random.random()),
        (random_string(5), random.randint(1, 1000)),
        (random_string(5), random.randint(100000, 10000000)),
        (random_string(5), random_string(6))
    ])
    def test_remove(self, key, value):
        '''
        @summary: Testing remove method of Dictionary API
        '''
        hashmap = {}
        hashmap[key] = value
        content = self.dict_obj.create(hashmap)
        self.dict_obj.remove(content, key)
        assert not self.dict_obj.contains(content, key)

    def test_toMap(self):
        '''
        @summary: Testing remove method of Dictionary API
        '''
        # TODO ios gets back {} for self.datatype.hashMap()
        hashmap = {}
        key = "Date_key"
        value = self.datatype.setDate()
        hashmap[key] = value
        key = "Double_key"
        value = random.uniform(1, 10)
        hashmap[key] = value
        key = "Float_key"
        value = random.random()
        hashmap[key] = value
        key = "Integer_key"
        value = random.randint(1, 1000)
        hashmap[key] = value
        key = "Long_key"
        value = random.randint(100000, 10000000)
        hashmap[key] = value
        key = "String_key"
        value = random_string(6)
        hashmap[key] = value

        content_dict = self.dict_obj.create(hashmap)
        result_dict = self.dict_obj.toMap(content_dict)
        assert self.datatype.compareHashMap(hashmap, result_dict)
