import uuid
import pytest
from keywords.utils import random_string
from CBLClient.Database import Database
from CBLClient.Collection import Collection
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.testkit import cluster
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.admin import Admin
from keywords import couchbaseserver
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from test_replication import verify_sgDocIds_cblDocIds

bucket = "data-bucket"


@pytest.fixture
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
    data = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {}}}}, "num_index_replicas": 0}
    sg_db = "db"

    sg_client = sg_url = sg_admin_url = None
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
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
    db_config = db.configure()

    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')

    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cbs_url = topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    cb_server.get_bucket_names()
    does_scope_exist = cb_server.does_scope_exist(bucket, scope)
    if does_scope_exist is False:
        cb_server.create_scope(bucket, scope)
        cb_server.create_collection(bucket, scope, collection)

    # sgw database creation
    if admin_client.does_db_exist(sg_db) is True:
        admin_client.delete_db(sg_db)
        admin_client.create_db(sg_db, data)
    else:
        admin_client.create_db(sg_db, data)
    log_info("sgw db created")
    log_info(admin_client.get_db_info(sg_db))
    log_info(admin_client.get_config())

    # cbl database, scope and collection creation
    cbl_db = db.create(cbl_db_name, db_config)
    created_collection = db.createCollection(cbl_db, collection, scope)
    log_info("cbl with collection created")

    # Create a user
    pre_test_user_exists = admin_client.does_user_exist(sg_db, sg_username)
    if pre_test_user_exists is False:
        sg_client.create_user(sg_admin_url, sg_db, sg_username, sg_password, auth=auth, channels=["ABC"])

    yield base_url, sg_blip_url, sg_url, sg_client, cbl_db, sg_db, scope, collection, created_collection, col_obj, doc_obj, auth, sg_admin_url, sg_username, sg_password, db_config


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("no_of_docs", [2])
def test_sync_scopeA_colA_to_scopeA_colA(scope_collection_test_fixture, teardown_doc_fixture, no_of_docs):
    # setup
    base_url, sg_blip_url, sg_url, sg_client, cbl_db, sg_db, scope, collection, created_collection, col_obj, doc_obj, auth, sg_admin_url, sg_username, sg_password, db_config = scope_collection_test_fixture
    db = Database(base_url)
    db.create_bulk_docs(no_of_docs, "cbl", db=cbl_db, channels=["ABC"], collection=created_collection)
    channels = ["ABC"]
    # setup replicator and replicate
    replicator = Replication(base_url)
    collections = []
    collections_configuration = []
    collections_configuration.append(replicator.collectionConfigure(channels=channels, collection=created_collection))
    log_info(collections_configuration)

    collections.append(created_collection)
    try:
        session, replicator_authenticator, repl = replicator.create_session_configure_replicate_collection(base_url, sg_admin_url, sg_db, sg_username, sg_client, sg_blip_url, continuous=True, replication_type="push", auth=auth, collections=collections, collection_configuration=collections_configuration)
    except Exception as e:
        pytest.fail("Replication failed due to " + str(e))

    # checking existence of doc after replication complete
    docs = []
    for i in range(0, no_of_docs):
        docId = "cbl_" + str(i)
        docs.append(sg_client.get_doc(sg_url, sg_db, docId, auth=session, scope=scope, collection=collection))
    assert len(docs) == no_of_docs, "Number of docs mismatched"
    # verify_sgDocIds_cblDocIds(sg_client=sg_client, url=sg_url, sg_db=sg_db, session=session, cbl_db=cbl_db, db=db)


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("no_of_docs", [2])
def test_sync_scopeA_colA_from_mulitple_cbl(scope_collection_test_fixture, teardown_doc_fixture, no_of_docs,):
    base_url, sg_blip_url, sg_url, sg_client, cbl_db, sg_db, scope, collection, created_collection, col_obj, doc_obj, auth, sg_admin_url, sg_username, sg_password, db_config = scope_collection_test_fixture
    db = Database(base_url)
    cbl_db1 = db.create(random_string(6), db_config)
    created_collection2 = db.createCollection(cbl_db1, collection, scope)
    cbl_db2 = db.create(random_string(6), db_config)
    created_collection3 = db.createCollection(cbl_db2, collection, scope)
    db.create_bulk_docs(no_of_docs, "cbl", db=cbl_db, channels=["ABC"], id_start_num=1, collection=created_collection)
    db.create_bulk_docs(no_of_docs, "cbl", db=cbl_db1, channels=["ABC"], id_start_num=50, collection=created_collection2)
    db.create_bulk_docs(no_of_docs, "cbl", db=cbl_db2, channels=["ABC"], id_start_num=100, collection=created_collection3)
    channels = ["ABC"]
    replicator = Replication(base_url)

    collections1 = []
    collections1.append(created_collection)
    collections_configuration1 = []
    collections_configuration1.append(replicator.collectionConfigure(channels=channels, collection=created_collection))

    collections2 = []
    collections_configuration2 = []
    collections2.append(created_collection2)
    collections_configuration2.append(replicator.collectionConfigure(channels=channels, collection=created_collection2))

    collections3 = []
    collections3.append(created_collection3)
    collections_configuration3 = []
    collections_configuration3.append(replicator.collectionConfigure(channels=channels, collection=created_collection3))

    authenticator = Authenticator(base_url)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, sg_username, auth=auth)
    session = cookie, session_id
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl_config1 = replicator.configureCollection(target_url=sg_blip_url, target_db=sg_db, replication_type="push", collection=collections1, collectionConfiguration=collections_configuration1, replicator_authenticator=replicator_authenticator)
    repl_config2 = replicator.configureCollection(target_url=sg_blip_url, target_db=sg_db, replication_type="push", collection=collections2, collectionConfiguration=collections_configuration2, replicator_authenticator=replicator_authenticator)
    repl_config3 = replicator.configureCollection(target_url=sg_blip_url, target_db=sg_db, replication_type="push", collection=collections3, collectionConfiguration=collections_configuration3, replicator_authenticator=replicator_authenticator)

    repl1 = replicator.create(repl_config1)
    repl2 = replicator.create(repl_config2)
    repl3 = replicator.create(repl_config3)

    replicator.start(repl1)
    replicator.start(repl2)
    replicator.start(repl3)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)

    sg_docs = sg_client.get_all_docs(sg_url, sg_db, auth=session)
    sg_docs = sg_docs['rows']
    assert len(sg_docs) == 6, "Not all replicated"
