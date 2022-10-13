import uuid
import pytest
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords import couchbaseserver
from libraries.testkit.cluster import Cluster
from keywords.constants import RBAC_FULL_ADMIN
from libraries.testkit.admin import Admin
from keywords.exceptions import RestError

# test file shared variables
bucket = "data-bucket"
sg_password = "password"
admin_client = cb_server = sg_username = channels = None
admin_auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]


@pytest.fixture
def teardown_doc_fixture():
    def _delete_doc_if_exist(sg_client, url, db, doc_id, auth, scope, collection):
        if sg_client.does_doc_exist(url, db, doc_id, scope=scope, collection=collection) is True:
            sg_client.delete_doc(url, db, doc_id, auth=auth, scope=scope, collection=collection)
    yield _delete_doc_if_exist


@pytest.fixture
def scopes_collections_tests_fixture(params_from_base_test_setup):
    try:  # To be able to teardon in case of a setup error
        # get/set the parameters
        global admin_client
        global cb_server
        global sg_username
        global channels
        session_id = pre_test_db_exists = pre_test_user_exists = None
        random_suffix = str(uuid.uuid4())[:8]
        db_prefix = "db_"
        scope_prefix = "scope_"
        collection_prefix = "collection_"
        db = db_prefix + random_suffix
        scope = scope_prefix + random_suffix
        collection = collection_prefix + random_suffix
        sg_username = "scopes_collections_user" + random_suffix
        channels = ["ABC"]
        data = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {}}}}, "num_index_replicas": 0}
        auth_session = sg_client = sg_url = sg_admin_url = auth_session = None
        cluster_config = params_from_base_test_setup["cluster_config"]
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        cluster_helper = ClusterKeywords(cluster_config)
        topology = cluster_helper.get_cluster_topology(cluster_config)
        cbs_url = topology["couchbase_servers"][0]
        sg_url = topology["sync_gateways"][0]["public"]
        cluster = Cluster(config=cluster_config)
        sg_client = MobileRestClient()
        cb_server = couchbaseserver.CouchbaseServer(cbs_url)
        admin_client = Admin(cluster.sync_gateways[0])
        sg_url = params_from_base_test_setup["sg_url"]

        # Scope creation on the Couchbase server
        does_scope_exist = cb_server.does_scope_exist(bucket, scope)
        if does_scope_exist is False:
            cb_server.create_scope(bucket, scope)
        cb_server.create_collection(bucket, scope, collection)

        # SGW database creation
        pre_test_db_exists = admin_client.does_db_exist(db)
        test_bucket_db = admin_client.get_bucket_db(bucket)
        if test_bucket_db is not None:
            admin_client.delete_db(test_bucket_db)
        if pre_test_db_exists is False:
            admin_client.create_db(db, data)

        # Create a user
        pre_test_user_exists = admin_client.does_user_exist(db, sg_username)
        if pre_test_user_exists is False:
            sg_client.create_user(sg_admin_url, db, sg_username, sg_password, auth=admin_auth)

        # Create a SGW session
        cookie, session_id = sg_client.create_session(sg_admin_url, db, sg_username, auth=admin_auth)
        auth_session = cookie, session_id
        yield sg_client, sg_url, sg_admin_url, auth_session, db, scope, collection
    except Exception as e:
        raise e
    finally:
        # Cleanup everything that was created
        if (session_id is not None) and (sg_client.does_session_exist(sg_admin_url, db=db, session_id=session_id) is True):
            sg_client.delete_session(sg_admin_url, db, session_id=session_id)
        if (pre_test_user_exists is not None) and (pre_test_user_exists is False):
            admin_client.delete_user_if_exists(db, sg_username)
        if (pre_test_db_exists is not None) and (pre_test_db_exists is False):
            if admin_client.does_db_exist(db) is True:
                admin_client.delete_db(db)
        cb_server.delete_scope_if_exists(bucket, scope)


@pytest.mark.syncgateway
@pytest.mark.collections
def test_document_only_under_named_scope(scopes_collections_tests_fixture, teardown_doc_fixture):

    # setup
    doc_prefix = "scp_tests_doc"
    doc_id = doc_prefix + "_0"
    sg_client, sg_url, sg_admin_url, auth_session, db, scope, collection = scopes_collections_tests_fixture
    if sg_client.does_doc_exist(sg_url, db, doc_id, auth_session, scope=scope, collection=collection) is False:
        sg_client.add_docs(sg_url, db, 1, doc_prefix, auth_session, scope=scope, collection=collection)
    teardown_doc_fixture(sg_client, sg_admin_url, db, doc_id, auth_session, scope, collection)

    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection when specifying the scope in the endpoint. The error: " + str(e))

    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection WITHOUT specifying the scope in the endoint. The error: " + str(e))

    #  exercise + verification
    with pytest.raises(Exception) as e:  # HTTPError doesn't work, for some  reason, but would be preferable
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope="_default", collection=collection)
    e.match("Not Found")


@pytest.mark.syncgateway
@pytest.mark.collections
def test_change_collection_name(scopes_collections_tests_fixture):
    """
    1. Upload a document to a collection
    2. Rename the collection by updating the config
    3. Check that the document is not accessiable in the new collection
    4. Rename the collection to the original collection
    5. Verify that the document is accessible again
    """
    # setup
    sg_client, sg_url, sg_admin_url, auth_session, db, scope, collection = scopes_collections_tests_fixture
    doc_prefix = "scp_tests_doc"
    doc_id = doc_prefix + "_0"
    new_collection_name = "new_collection_test"

    # 1. Upload a document to a collection
    if sg_client.does_doc_exist(sg_url, db, doc_id, auth=auth_session, scope=scope, collection=collection) is False:
        sg_client.add_docs(sg_url, db, 1, doc_prefix, auth=auth_session, scope=scope, collection=collection)

    # 2. Rename the collection by updating the config
    cb_server.create_collection(bucket, scope, new_collection_name)
    rename_a_single_collection(db, scope, new_collection_name)

    #  exercise + verification
    with pytest.raises(Exception) as e:  # HTTPError doesn't work, for some reason, but would be preferable
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope, collection=new_collection_name)
    e.match("Not Found")

    # 4. Rename the collection to the original collection
    rename_a_single_collection(db, scope, collection)

    # 5. Verify that the document is accessible again
    try:
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope, collection=collection)
    except Exception as e:
        pytest.fail("The document could not be read from the collection after it was renamed and renamed back. The error: " + str(e))


@pytest.mark.syncgateway
@pytest.mark.collections
def test_collection_channels(scopes_collections_tests_fixture):
    """
    1. Create 3 users with different channels, one is in the wildcard channel
    2. Upload the documents to the collection, under the user's channels and one to the public channel
    3. Get all the documents using _all_docs
    4. Check that the users can only see the documents in their channel
    5. Check that the users see the shared document in the channel
    6. Check that _bulk_get cannot get documents that are not in the user's channel
    7. Check that _bulk_get can get documents that are in the user's channel
    8. Check that _bulk_get cannot get a document from the "right" channel but the wrong collection
    """
    # setup
    sg_client, sg_url, sg_admin_url, auth_session, db, scope, collection = scopes_collections_tests_fixture
    random_str = str(uuid.uuid4())[:6]
    test_user_1 = "cu1_" + random_str
    test_user_2 = "cu2_" + random_str
    test_wildcard_user = "wu_" + random_str
    user_1_doc_prefix = "user_1_doc_" + random_str
    user_2_doc_prefix = "user_2_doc_" + random_str
    shared_doc_prefix = "shared_" + random_str
    channels_user_1 = ["USER1_CHANNEL"]
    channels_user_2 = ["USER2_CHANNEL"]
    auth_user_1 = test_user_1, sg_password
    auth_user_2 = test_user_2, sg_password
    auth_wildcard_user = test_wildcard_user, sg_password

    # 1. Create 3 users with different channels, one is in the wildcard channel
    sg_client.create_user(sg_admin_url, db, test_user_1, sg_password, channels=channels_user_1, auth=admin_auth)
    sg_client.create_user(sg_admin_url, db, test_user_2, sg_password, channels=channels_user_2, auth=admin_auth)
    sg_client.create_user(sg_admin_url, db, test_wildcard_user, sg_password, channels=["*"], auth=admin_auth)

    # 2. Upload the documents to the collection
    sg_client.add_docs(sg_url, db, 3, user_1_doc_prefix, auth=auth_user_1, channels=channels_user_1, scope=scope, collection=collection)
    sg_client.add_docs(sg_url, db, 3, user_2_doc_prefix, auth=auth_user_2, channels=channels_user_2, scope=scope, collection=collection)
    sg_client.add_docs(sg_admin_url, db, 1, shared_doc_prefix, auth=auth_session, channels=["!"], scope=scope, collection=collection)

    # 3. Get all the documents using _all_docs
    user_1_docs = sg_client.get_all_docs(url=sg_url, db=db, auth=auth_user_1, include_docs=True)
    user_2_docs = sg_client.get_all_docs(url=sg_url, db=db, auth=auth_user_2, include_docs=True)
    wildcard_user_docs = sg_client.get_all_docs(url=sg_url, db=db, auth=auth_wildcard_user, include_docs=True)

    user_1_docs_ids = [doc["id"] for doc in user_1_docs["rows"]]
    user_2_docs_ids = [doc["id"] for doc in user_2_docs["rows"]]
    wildcard_user_docs_ids = [doc["id"] for doc in wildcard_user_docs["rows"]]
    shared_found_user_1 = False
    shared_found_user_2 = False

    # 4. Check that the users can only see the documents in their channels
    for doc in user_1_docs_ids:
        if user_2_doc_prefix in doc:
            pytest.fail("A document is available in a channel that it was not assigned to. Document prefix: " + user_2_doc_prefix + ". The document: " + doc)
        if shared_doc_prefix in doc:
            shared_found_user_1 = True
        if doc not in wildcard_user_docs_ids:
            pytest.fail("The document " + doc + " was not accessiable even though the user was given all documents access")
    for doc in user_2_docs_ids:
        if user_1_doc_prefix in doc:
            pytest.fail("A document is available in a channel that it was not assigned to. Document prefix: " + user_1_doc_prefix + ". The document: " + doc)
        if shared_doc_prefix in doc:
            shared_found_user_2 = True
        if doc not in wildcard_user_docs_ids:
            pytest.fail("The document " + doc + " was not accessiable even though the user was given all documents access")

    # 5. Check that the users see the shared document in their channels
    assert (shared_found_user_1 and shared_found_user_2), "The shared document was not found for one of the users. user1: " + shared_found_user_1 + " user2: " + shared_found_user_2
    assert (shared_doc_prefix in doc for doc in wildcard_user_docs_ids), "The shared document was not accessiable VIA the wildcard channel"

    # 6. Check that _bulk_get cannot get documents that are not in the user's channel
    with pytest.raises(RestError) as e:  # HTTPError doesn't work, for some  reason, but would be preferable
        sg_client.get_bulk_docs(url=sg_url, db=db, doc_ids=user_2_docs_ids, auth=auth_user_1, scope=scope, collection=collection)
    assert "'status': 403" in str(e)
    # 7. Check that _bulk_get can get documents that are in the user's channel
    sg_client.get_bulk_docs(url=sg_url, db=db, doc_ids=user_1_docs_ids, auth=auth_user_1, scope=scope, collection=collection)

    # 8. Check that _bulk_get cannot get a document from the "right" channel but the wrong collection
    with pytest.raises(Exception) as e:
        sg_client.get_bulk_docs(url=sg_url, db=db, doc_ids=user_1_docs_ids, auth=auth_user_1, scope=scope, collection="fake_collection")
    e.match("Not Found")


def rename_a_single_collection(db, scope, new_name):
    data = {"bucket": bucket, "scopes": {scope: {"collections": {new_name: {}}}}, "num_index_replicas": 0}
    admin_client.post_db_config(db, data)
    admin_client.wait_for_db_online(db, 60)
