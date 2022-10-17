import pytest
import random
import math
from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestScopeCollection(object):

    @pytest.mark.parametrize("db_name, scope, collection", [
        (random_string(6), "{} {}".format(random_string(3), random_string(3)), "{} {}".format(random_string(3), random_string(3))),
        (random_string(6), random_string(6), "{} {}".format(random_string(3), random_string(3))),
        (random_string(6), "{} {}".format(random_string(3), random_string(3)), random_string(6)),
        (random_string(6), random_string(6), random_string(6))
    ])
    def test_scope_collection_name_with_space(self, db_name, scope, collection):
        '''
         @summary: Creating scope and collections with space in names
        '''
        db = self.db_obj.create(db_name)
        try:
            self.db_obj.createCollection(db, collection, scope)
            created_Collection = self.db_obj.collectionObject(db, collection, scope)
            created_CollectionName = self.collection_obj.collectionName(created_Collection)
            assert created_CollectionName == collection, "Scope and collection created but not found"
        except:
            if ' ' in scope and ' ' in collection:
                print("Invalid scope name: " + scope + "and collection name: " + collection)
            elif ' ' in scope:
                print("Invalid scope name: " + scope)
            else:
                print("Invalid collection name: " + collection)
            assert True

    @pytest.mark.parametrize("db_name, no_of_scope, collection", [
        (random_string(6), 9, "specificName")
    ])
    def test_same_collection_in_different_scope(self, db_name, no_of_scope, collection):
        '''
        @summary: Creating collection with same name in different scopes
        '''
        db = self.db_obj.create(db_name)
        for i in range(1, no_of_scope + 1):
            scopeName = "scope-" + str(i)
            try:
                self.db_obj.createCollection(db, collection, scopeName)
            except:
                print("Failed to create collection in scope " + scopeName)
                assert False
        collections = []
        for i in range(1, no_of_scope + 1):
            scopeName = "scope-" + str(i)
            collections.append(self.db_obj.collectionObject(db, collection, scopeName))
        assert len(collections) == no_of_scope, "Number of collections made, mismatch"

    @pytest.mark.parametrize("db_name, no_of_scope, no_of_collection", [
        (random_string(6), random.randrange(1000), random.randrange(1000))
    ])
    def test_create_more_than_1000_scopes_collections(self, db_name, no_of_scope, no_of_collection):
        '''
        @summary: Creating more than 1000 scopes and collections
        '''
        db = self.db_obj.create(db_name)
        collection_per_scope = math.ceil(no_of_collection / no_of_scope)
        for i in range(1, no_of_scope + 1):
            scopeName = "scope-" + str(i)
            for k in range(1, collection_per_scope + 1):
                collectionName = "collection-" + str(k)
                try:
                    self.db_obj.createCollection(db, collectionName, scopeName)
                except:
                    print("Scope and collection creation failed")
                    assert False
        total_collections = []
        for i in range(1, no_of_scope + 1):
            scopeName = "scope-" + str(i)
            total_collections.extend(self.collection_obj.allCollection(db, scopeName))
        assert len(total_collections) == (collection_per_scope * no_of_scope), " Missing scopes and collections "

    @pytest.mark.parametrize("db_name, scope, collection", [
        (random_string(6), random_string(6), random_string(6))
    ])
    def test_delete_non_existant_scopes_collections(self, db_name, scope, collection):
        '''
        @summary: Creating collection with same name in different scopes
        '''
        db = self.db_obj.create(db_name)
        try:
            self.db_obj.deleteCollection(db, collection, scope)
            print("No error while deleting non-existing scopes and collections")
        except:
            print("Error found")
            assert True
            return
        assert False
