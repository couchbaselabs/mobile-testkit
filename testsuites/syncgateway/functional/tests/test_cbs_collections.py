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
collection = "collection1"
data = {"bucket": bucket, "num_index_replicas": 0}


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
        random_suffix = str(uuid.uuid4())[:8]
        scope_prefix = "scope"
        db_prefix = "scopes_and_collections_db"
        db = db_prefix + random_suffix
        scope = scope_prefix + random_suffix
        sg_username = "scopes_collections_user"
        sg_password = "password"
        channels = ["ABC"]
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
        session_id = None
        cookie, session_id = sg_client.create_session(sg_admin_url, db, sg_username, auth=auth)
        auth_session = cookie, session_id

        create_sgw_collection(admin_client, db, scope, bucket)

    finally:
        yield sg_client, sg_url, sg_admin_url, auth_session, db, scope
        # Cleanup everything the was created
        if sg_client.does_session_exist(sg_admin_url, db=db, session_id=session_id) is True:
            sg_client.delete_session(sg_admin_url, db, session_id=session_id)
        if pre_test_user_exists is False:
            admin_client.delete_user_if_exists(db, sg_username)
        delete_scopes_from_sgw_db(db, admin_client)
        if pre_test_db_exists is False:
            if admin_client.does_db_exist(db) is True:
                admin_client.delete_db(db)
        cb_server.delete_scope_if_exists(bucket, scope)


@pytest.mark.syncgateway
@pytest.mark.collections
def test_document_only_under_default_scope(scopes_collections_tests_fixture, teardown_doc_fixture):

    # setup
    doc_prefix = "default_scope_doc"
    doc_id = doc_prefix + "_0"
    sg_client, sg_url, sg_admin_url, auth_session, db, scope = scopes_collections_tests_fixture
    if sg_client.does_doc_exist(sg_url, db, doc_id, auth_session) is False:
        sg_client.add_docs(sg_url, db, 1, doc_prefix, auth_session)
    teardown_doc_fixture(sg_client, sg_admin_url, db, doc_id, auth_session)

    # exercise + verification
    with pytest.raises(Exception) as e:  # HTTPError doesn't work, for some  reason, but would be preferable
        sg_client.get_doc(sg_admin_url, db, doc_id, auth=auth_session, scope=scope)
    e.match("Not Found")


def create_sgw_collection(admin_client, db, scope_to_add, bucket_to_add_to):
    config = {"bucket": bucket_to_add_to, "scopes": {scope_to_add: {"collections": {collection: {}}}}}
    admin_client.post_db_config(db, config)


def delete_scopes_from_sgw_db(db, admin_client):
    db_config = admin_client.get_db_config(db)
    db_config["scopes"] = {}
    admin_client.post_db_config(db, db_config)
