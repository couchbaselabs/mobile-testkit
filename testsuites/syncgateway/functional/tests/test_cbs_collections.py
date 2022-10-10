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


@pytest.fixture
def teardown_doc_fixture():
    def _delete_doc_if_exist(sg_client, url, db, doc_id, auth):
        if sg_client.does_doc_exist(url, db, doc_id) is True:
            sg_client.delete_doc(url, db, doc_id, auth=auth)
    yield _delete_doc_if_exist


@pytest.fixture
def scopes_collections_tests_fixture(params_from_base_test_setup):
    try:  # To be able to teardon in case of a setup error
        # get/set the parameters
        session_id = None
        pre_test_db_exists = None
        pre_test_user_exists = None
        random_suffix = str(uuid.uuid4())[:8]
        db_prefix = "db_"
        scope_prefix = "scope_"
        collection_prefix = "collection_"
        db = db_prefix + random_suffix
        scope = scope_prefix + random_suffix
        collection = collection_prefix + random_suffix
        sg_username = "scopes_collections_user" + random_suffix
        sg_password = "password"
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
        # Cleanup everything the was created
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
    if sg_client.does_doc_exist(sg_url, db, doc_id, auth_session) is False:
        sg_client.add_docs(sg_url, db, 1, doc_prefix, auth_session)
    teardown_doc_fixture(sg_client, sg_admin_url, db, doc_id, auth_session)

    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection when specifying the scope in the endpoint. The error: " + str(e))

    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection WITHOUT specifying the scope in the endoint. The error: " + str(e))

    #  exercise + verification
    with pytest.raises(Exception) as e:  # HTTPError doesn't work, for some  reason, but would be preferable
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope="_default", collection=collection)
    e.match("Not Found")
