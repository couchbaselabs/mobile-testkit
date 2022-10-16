import random
import pytest
from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestBasicSC(object):

    def test_create_scope(self, scope_name):
        ''' Create scope with different name '''
        self.server_obj.create_scope(scope_name)

    def test_create_collection(self, scope_name, collection_name):
        '''
        Test create collection
        '''
        self.server_obj.create_collection()

    def test_create_scope_already_exist(self, scope_name):
        '''
        @summary: Testing count method of Dictionary API
        '''
        self.server_obj.create_scope(scope_name)
        try:
            self.server_obj.create_scope(scope_name)
        except Exception as e:
            if "Fail" in str(e):
                print("Test failed as expected")
                pass
            else:
                raise("Server could create another scope with same name")
        
    def test_remove_scope(self, scope_name):
        '''
        @summary: Testing remove scope
        '''
        self.server_obj.remove(scope_name, collection_name)

    def test_remove_collection(self, scope_name, collection_name):
        '''
        @summary: Testing remove collection
        '''
        self.server_obj.remove(scope_name, collection_name)

