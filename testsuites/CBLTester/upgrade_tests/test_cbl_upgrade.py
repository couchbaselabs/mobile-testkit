import pytest
import random
import time
import os

from CBLClient.Database import Database
from keywords.utils import log_info
from CBLClient.Replication import Replication
from keywords.MobileRestClient import MobileRestClient
from CBLClient.Authenticator import Authenticator
from libraries.testkit.cluster import Cluster
from couchbase.n1ql import N1QLQuery
from couchbase.bucket import Bucket
from keywords.constants import SDK_TIMEOUT
from CBLClient.MemoryPointer import MemoryPointer
from keywords.couchbaseserver import CouchbaseServer
from CBLClient.Query import Query


@pytest.mark.listener
@pytest.mark.upgrade_test
def test_upgrade_cbl(params_from_base_suite_setup):
    """
    @summary:
    1. Migrate older-pre-built db to a provided cbl app
    2. Start the replication and replicate db to cluster
    3. Running few query tests
        a. Run Query test for Any operator
        b. Run Query test for Between operator
        c. Run FTS Query test
        d. Run Join Query test 
    4. Perform mutation operations
        a. Add new docs and replicate to cluster
        b. Update docs for migrated db and replicate to cluster
        c. Delete docs from migrated db and replicate to cluster
    """
    base_url = params_from_base_suite_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_config = params_from_base_suite_setup["sg_config"]
    cbs_ip = params_from_base_suite_setup["cbs_ip"]
    server_url = params_from_base_suite_setup["server_url"]
    db = Database(base_url)

    cbl_db, upgrade_cbl_db_name = _upgrade_db(params_from_base_suite_setup)
    cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    assert len(cbl_doc_ids) == 31591
    get_doc_id_from_cbs_query = 'select meta().id from `{}` where meta().id not' \
                                ' like "_sync%" ORDER BY id'.format("travel-sample")
    # Replicating docs to CBS
    sg_client = MobileRestClient()
    replicator = Replication(base_url)
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client.create_user(sg_admin_url, sg_db, username, password)
    authenticator = Authenticator(base_url)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, replication_type="push", continuous=True,
                                       replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, sleep_time=10, max_times=500)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed
    replicator.stop(repl)

    password = "password"
    cbs_bucket = "travel-sample"
    server = CouchbaseServer(server_url)
    server._create_internal_rbac_bucket_user(cbs_bucket, cluster_config=cluster_config)
    log_info("Connecting to {}/{} with password {}".format(cbs_ip, cbs_bucket, password))
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, cbs_bucket), password=password, timeout=SDK_TIMEOUT)
    log_info("Creating primary index for {}".format(cbs_bucket))
    n1ql_query = "create primary index index1 on `{}`".format(cbs_bucket)
    query = N1QLQuery(n1ql_query)
    sdk_client.n1ql_query(query).execute()
    new_cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    cbs_doc_ids = []
    for row in sdk_client.n1ql_query(get_doc_id_from_cbs_query):
        cbs_doc_ids.append(row["id"])
    log_info("cbl_docs {}, cbs_docs {}".format(len(cbs_doc_ids), len(new_cbl_doc_ids)))
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Total no. of docs are different in CBS and CBL app"

    # Running selected Query tests
    # 1. Checking for Any operator
    # updating some docs to more than 128 times to reproduce issue - https://issues.couchbase.com/browse/CBSE-6844
    qy = Query(base_url)
    docs_to_update = random.sample(cbl_doc_ids, 20)
    db.update_bulk_docs(database=cbl_db, number_of_updates=129, doc_ids=docs_to_update)
    new_cbl_doc_ids = qy.query_any_operator(cbl_db, "schedule", "departure", "departure.utc",
                                            "23:41:00", "type", "route")
    n1ql_query = 'select meta().id from `travel-sample` where type="route" ' \
                 'AND ANY departure IN schedule SATISFIES departure.utc > "23:41:00" END;'
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    cbs_doc_ids = []
    for row in sdk_client.n1ql_query(query):
        cbs_doc_ids.append(row["id"])
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Any operator query output doesn't match"

    # 2. Checking for Between Operator
    new_cbl_doc_ids = qy.query_between(cbl_db, id, 1000, 2000)
    n1ql_query = 'select meta().id from `travel-sample` where {} between 1000 and 2000 order by meta().id asc'
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    cbs_doc_ids = []

    for row in sdk_client.n1ql_query(query):
        cbs_doc_ids.append(row)
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Between operator query output doesn't match"

    # 3. Checking for FTS with ranking
    limit = 10
    result_set = qy.query_fts_with_ranking(cbl_db, "content", "beautiful", "landmark", limit)
    new_cbl_doc_ids = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            new_cbl_doc_ids.append(result)
            log_info(result)
    assert 0 < len(new_cbl_doc_ids) <= limit, "FTS ranking query result doesn't match with expected result"

    # 4. Checking for Inner Join query
    result_set = qy.query_inner_join(cbl_db, "airline", "sourceairport", "country", "country",
                                     "stops", "United States", 0, "icao", "destinationairport", limit)

    new_cbl_doc_ids = []
    for docs in result_set:
        new_cbl_doc_ids.append(docs)

    assert len(new_cbl_doc_ids) == limit
    log_info("Found {} docs".format(len(new_cbl_doc_ids)))

    # Adding few docs to db
    new_doc_ids = db.create_bulk_docs(number=5, id_prefix="new_cbl_docs", db=cbl_db)

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    new_cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    cbs_docs = sg_client.get_all_docs(sg_admin_url, sg_db, session)["rows"]
    cbs_doc_ids = [doc["id"] for doc in cbs_docs]
    for new_doc_id in new_doc_ids:
        log_info("Checking if new doc - {} replicated to CBS".format(new_doc_id))
        assert new_doc_id in cbs_doc_ids, "New Docs failed to get replicated"
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Total no. of docs are different in CBS and CBL app"

    # updating old docs
    doc_ids_to_update = random.sample(cbl_doc_ids, 5)
    docs = db.getDocuments(cbl_db, doc_ids_to_update)
    for doc_id in docs:
        log_info("Updating CBL Doc - {}".format(doc_id))
        data = docs[doc_id]
        data["new_field"] = "test_string_for_{}".format(doc_id)
        db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbs_docs = sg_client.get_all_docs(sg_admin_url, sg_db, session)["rows"]
    cbs_doc_ids = [doc["id"] for doc in cbs_docs]

    for doc_id in doc_ids_to_update:
        log_info("Checking for updates in doc on CBS: {}".format(doc_id))
        sg_data = sg_client.get_doc(url=sg_admin_url, db=sg_db, doc_id=doc_id, auth=session)
        assert "new_field" in sg_data, "Updated docs failed to get replicated"
    new_cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)

    assert len(new_cbl_doc_ids) == len(cbs_doc_ids), "Total no. of docs are different in CBS and CBL app"
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Total no. of docs are different in CBS and CBL app"

    # deleting some of migrated docs
    doc_ids_to_delete = random.sample(cbl_doc_ids, 5)
    log_info("Deleting docs from CBL - {}".format(",".join(doc_ids_to_delete)))
    db.delete_bulk_docs(cbl_db, doc_ids_to_delete)

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbs_docs = sg_client.get_all_docs(sg_admin_url, sg_db, session)["rows"]
    cbs_doc_ids = [doc["id"] for doc in cbs_docs]
    for doc_id in doc_ids_to_delete:
        assert doc_id not in cbs_doc_ids, "Deleted docs failed to get replicated"

    new_cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    assert sorted(cbs_doc_ids) == sorted(new_cbl_doc_ids), "Total no. of docs are different in CBS and CBL app"

    # Cleaning the database , tearing down
    db_path = db.getPath(cbl_db).rstrip("/\\")
    if '\\' in db_path:
        db_path = '\\'.join(db_path.split('\\')[:-1])
    else:
        db_path = '/'.join(db_path.split('/')[:-1])
    if db.exists(upgrade_cbl_db_name, db_path):
        log_info("Delete DB - {}".format(upgrade_cbl_db_name))
        db.deleteDB(cbl_db)


@pytest.mark.listener
@pytest.mark.upgrade_test
def test_queries_on_upgrade_cbl(params_from_base_suite_setup):
    """
    @summary:
    1. Upgrade the db from lower CBl version
    2. Run all the query tests on upgraded db
    """
    upgraded_liteserv_version = params_from_base_suite_setup["upgraded_liteserv_version"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    sg_version = params_from_base_suite_setup["sg_version"]
    server_version = params_from_base_suite_setup["server_version"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    base_url = params_from_base_suite_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_config = params_from_base_suite_setup["sg_config"]

    cbl_db, upgraded_cbl_db_name = _upgrade_db(params_from_base_suite_setup)

    # Replicating docs to CBS
    sg_client = MobileRestClient()
    replicator = Replication(base_url)
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client.create_user(sg_admin_url, sg_db, username, password)
    authenticator = Authenticator(base_url)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, replication_type="push", continuous=True,
                                       replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, sleep_time=10, max_times=500)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed
    replicator.stop(repl)

    # Runing Query tests
    log_info("Running Query tests")
    directory = os.getcwd()
    os.chdir(directory)
    cmd = ["{}/testsuites/CBLTester/CBL_Functional_tests/SuiteSetup_FunctionalTests".format(os.getcwd()),
           "--liteserv-version={}".format(upgraded_liteserv_version), "--skip-provisioning",
           "--liteserv-host={}".format(liteserv_host), "--liteserv-port=8080",
           "--sync-gateway-version={}".format(sg_version), "--mode=cc", "--server-version={}".format(server_version),
           "--liteserv-platform={}".format(liteserv_platform), "--create-db-per-suite={}".format(upgraded_cbl_db_name)
           ]
    pytest.main(cmd)


def _upgrade_db(args):
    base_liteserv_version = args["base_liteserv_version"]
    upgraded_liteserv_version = args["upgraded_liteserv_version"]
    liteserv_platform = args["liteserv_platform"]
    upgrade_cbl_db_name = "upgarded_db"
    base_url = args["base_url"]
    encrypted_db = args["encrypted_db"]
    db_password = args["db_password"]
    utils_obj = args["utils_obj"]

    if base_liteserv_version > upgraded_liteserv_version:
        pytest.skip("Can't upgrade from higher version db to lower version db")

    supported_base_liteserv = ["1.4", "2.0.0", "2.1.5", "2.5.0"]
    db = Database(base_url)
    if encrypted_db:
        if base_liteserv_version < "2.1.5":
            pytest.skip("Encyption is supported from 2.1.0 onwards."
                        "{} doesn't have encrypted db upgrade support".format(base_liteserv_version))
        db_config = db.configure(password=db_password)
        db_prefix = "travel-sample-encrypted"
    else:
        db_config = db.configure()
        db_prefix = "travel-sample"

    temp_db = db.create("temp_db", db_config)
    time.sleep(1)
    new_db_path = db.getPath(temp_db)
    delimiter = "/"
    if liteserv_platform == "net-msft" or liteserv_platform == "net-uwp":
        delimiter = "\\"
    new_db_path = "{}".format(delimiter).join(new_db_path.split(delimiter)[:-2]) +\
                  "{}{}.cblite2".format(delimiter, upgrade_cbl_db_name)
    db.deleteDB(temp_db)

    old_liteserv_db_name = ""
    if base_liteserv_version in supported_base_liteserv:
        old_liteserv_db_name = db_prefix + "-" + base_liteserv_version
    else:
        pytest.skip("Run test with one of supported base liteserv version - ".format(supported_base_liteserv))

    if liteserv_platform == "android":
        prebuilt_db_path = "/assets/{}.cblite2.zip".format(old_liteserv_db_name)
    elif liteserv_platform == "xamarin-android":
        prebuilt_db_path = "{}.cblite2.zip".format(old_liteserv_db_name)
    else:
        prebuilt_db_path = "Databases/{}.cblite2".format(old_liteserv_db_name)

    log_info("Copying db of CBL-{} to CBL-{}".format(base_liteserv_version, upgraded_liteserv_version))
    prebuilt_db_path = db.get_pre_built_db(prebuilt_db_path)
    assert "Copied" == utils_obj.copy_files(prebuilt_db_path, new_db_path)
    cbl_db = db.create(upgrade_cbl_db_name, db_config)
    assert isinstance(cbl_db, MemoryPointer), "Failed to migrate db from previous version of CBL"
    return cbl_db, upgrade_cbl_db_name
