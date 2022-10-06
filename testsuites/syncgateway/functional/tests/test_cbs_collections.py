import uuid
import pytest
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords import couchbaseserver
from libraries.testkit.cluster import Cluster
from keywords.constants import RBAC_FULL_ADMIN
from libraries.testkit.admin import Admin

# test file shared variables
bucket = "data-bucket"
sg_password = "password"
admin_client = cb_server = sg_username = channels = None


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
        auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]

        # Scope creation on the Couchbase server
        does_scope_exist = cb_server.does_scope_exist(bucket, scope)
        if does_scope_exist is False:
            cb_server.create_scope(bucket, scope)
        cb_server.create_collection(bucket, scope, collection)

        # SGW database creation
        pre_test_db_exists = admin_client.does_db_exist(db)
        if pre_test_db_exists is False:
            admin_client.create_db(db, data)

        # Create a user
        pre_test_user_exists = admin_client.does_user_exist(db, sg_username)
        if pre_test_user_exists is False:
            sg_client.create_user(sg_admin_url, db, sg_username, sg_password, channels, auth)

        # Create a SGW session
        cookie, session_id = sg_client.create_session(sg_admin_url, db, sg_username, auth=auth)
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
    # setup
    sg_client, sg_url, sg_admin_url, auth_session, db, scope, collection = scopes_collections_tests_fixture
    random_str = str(uuid.uuid4())[:6]
    doc_prefix = "scp_tests_doc_" + random_str
    channels_tests_doc_prefix = "channels_doc_" + random_str
    sg_channel_test_username = "channel_test_user" + random_str
    channels_test_channel = ["CHANNEL_TEST"]
    auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]
    sg_client.create_user(sg_admin_url, db, sg_channel_test_username, sg_password, channels=channels_test_channel, auth=auth)
    auth_scopes_user = sg_username, sg_password
    auth_channels_user = sg_channel_test_username, sg_password

    sg_client.add_docs(sg_url, db, 3, doc_prefix, auth_scopes_user, channels=channels, scope=scope, collection=collection)
    sg_client.add_docs(sg_url, db, 3, channels_tests_doc_prefix, auth_channels_user, channels=channels_test_channel, scope=scope, collection=collection)

    scopes_tests_docs = sg_client.get_all_docs(url=sg_url, db=db, auth=auth_scopes_user, include_docs=True)
    channels_test_docs = sg_client.get_all_docs(url=sg_url, db=db, auth=auth_channels_user, include_docs=True)

    scopes_tests_docs_ids = [doc["id"] for doc in scopes_tests_docs["rows"]]
    channels_test_docs_ids = [doc["id"] for doc in channels_test_docs["rows"]]
    for doc in scopes_tests_docs_ids:
        if channels_tests_doc_prefix in doc:
            pytest.fail("A document is available in a channel that it was not assigned to. Document prefix: " + doc_prefix + ". The document: " + doc)
    for doc in channels_test_docs_ids:
        if doc_prefix in doc:
            pytest.fail("A document is available in a channel that it was not assigned to. Document prefix: " + doc_prefix + ". The document: " + doc)


def rename_a_single_collection(db, scope, new_name):
    data = {"bucket": bucket, "scopes": {scope: {"collections": {new_name: {}}}}, "num_index_replicas": 0}
    admin_client.post_db_config(db, data)
    admin_client.wait_for_db_online(db, 60)
