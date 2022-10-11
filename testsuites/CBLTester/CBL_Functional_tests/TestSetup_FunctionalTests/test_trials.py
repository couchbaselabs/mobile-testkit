import uuid
import pytest
from CBLClient.Database import Database
from CBLClient.Collection import Collection
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN

bucket = "data_bucket"


@pytest.fixture(scope="function")
def teardown_doc_fixture():
    def _delete_doc_if_exist(sg_client, url, db, doc_id, auth):
        if sg_client.does_doc_exist(url, db, doc_id) is True:
            sg_client.delete_doc(url, db, doc_id, auth=auth)
    yield _delete_doc_if_exist


@pytest.fixture(scope="function")
def scope_collection_test_fixture(params_from_base_test_setup):
    random_suffix = str(uuid.uuid4())[:8]
    db_prefix = "db_"
    scope_prefix = "scope_"
    collection_prefix = "collection_"
    cbl_db_name = db_prefix + random_suffix
    scope = scope_prefix + random_suffix
    collection = collection_prefix + random_suffix
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    sg_username = "scope_collection_user" + random_suffix
    sg_password = "password"
    channels = ["ABC"]
    data = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {}}}}, "num_index_replicas": 0}
    sg_db = "sdb"

    auth_session = sg_client = sg_url = sg_admin_url = auth_session = None
    cluster_config = params_from_base_test_setup["cluster_config"]
    
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    auth = need_sgw_admin_auth and [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']] or None
    admin_client = Admin(c.sync_gateways[0])
    db = Database(base_url)
    col_obj = Collection(base_url)
    doc_obj = Document(base_url)
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    db_config = db.configure()

    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')

    # sgw database creation
    pre_test_db_exists = admin_client.does_db_exist(sg_db)
    if pre_test_db_exists is False:
        admin_client.create_db(sg_db, data)

    # cbl database, scope and collection creation
    cbl_db = db.create(cbl_db_name, db_config)
    created_collection = db.createCollection(cbl_db, collection, scope)

    # Create a user
    pre_test_user_exists = admin_client.does_user_exist(sg_db, sg_username)
    if pre_test_user_exists is False:
        sg_client.create_user(sg_admin_url, sg_db, sg_username, sg_password, channels, auth)

    # Create a SGW session
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, sg_username, auth=auth)
    auth_session = cookie, session_id
    yield base_url, sg_blip_url, sg_url, sg_client, cbl_db, sg_db, auth_session, scope, collection, created_collection, col_obj, doc_obj, sg_admin_url


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.collections
@pytest.mark.ios
def test_sync_scopeA_colA_to_scopeA_colA(scope_collection_test_fixture, teardown_doc_fixture):
    # setup
    doc_prefix = "doc_"
    doc_id = doc_prefix + "_0"
    base_url, sg_blip_url, sg_url, sg_client, cbl_db, sg_db, auth_session, scope, collection, created_collection, col_obj, doc_obj, sg_admin_url = scope_collection_test_fixture
    doc = doc_obj.create(doc_id=doc_id)
    log_info("Saving data in cbl in user defined scope and collection")
    col_obj.saveDocument(created_collection, doc)
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"

    # setup replicator
    replicator = Replication(base_url)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels_sg, sg_client, cbl_db, sg_blip_url, continuous=True, replication_type="push_pull", auth=auth, collection=created_collection)

    teardown_doc_fixture(sg_client, sg_admin_url, sg_db, doc_id, auth_session)
    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, sg_db, doc_id, auth=auth_session, scope=scope, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection when specifying the scope in the endpoint. The error: " + str(e))

    # exercise + verification
    try:
        sg_client.get_doc(sg_admin_url, sg_db, doc_id, auth=auth_session, collection=collection)
    except Exception as e:
        pytest.fail("There was a problem reading the document from a collection WITHOUT specifying the scope in the endoint. The error: " + str(e))

    #  exercise + verification
    with pytest.raises(Exception) as e:  # HTTPError doesn't work, for some  reason, but would be preferable
        sg_client.get_doc(sg_admin_url, sg_db, doc_id, auth=auth_session, scope="_default", collection=collection)
    e.match("Not Found")
    assert True
