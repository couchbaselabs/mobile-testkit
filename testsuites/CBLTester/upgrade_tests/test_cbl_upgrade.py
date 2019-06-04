import pytest
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
import time

@pytest.mark.listener
@pytest.mark.upgrade_test
def test_upgrade_cbl(params_from_base_suite_setup):
    base_liteserv_version = "2.1.5"#params_from_base_suite_setup["base_liteserv_version"]
    upgraded_liteserv_version = params_from_base_suite_setup["upgraded_liteserv_version"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    upgrade_cbl_db_name = "upgarded_db"
    base_url = params_from_base_suite_setup["base_url"]
    upgrade_from_encrypted_db = True#params_from_base_suite_setup["encrypted_db"]
    db_password = params_from_base_suite_setup["db_password"]
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    sg_version = params_from_base_suite_setup["sync_gateway_version"]
    server_version = params_from_base_suite_setup["server_version"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_config = params_from_base_suite_setup["sg_config"]
    cbs_ip = params_from_base_suite_setup["cbs_ip"]
    utils_obj = params_from_base_suite_setup["utils_obj"]


    supported_base_liteserv = ["1.4", "2.0.0", "2.1.5", "2.5.0"]
    db = Database(base_url)
    if upgrade_from_encrypted_db:
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
#     db.copyDatabase(old_db_path, upgrade_cbl_db_name, db_config)
    cbl_db = db.create(upgrade_cbl_db_name, db_config)
    cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    assert len(cbl_doc_ids) == 31591

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
    repl_config = replicator.configure(cbl_db, sg_blip_url, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl,sleep_time=10)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
#     assert total == completed
    log_info("total:", total)
    log_info("completed:", completed)
    replicator.stop(repl)
 
#     log_info("Creating primary index for {}".format("travel-sample"))
#     n1ql_query = 'create primary index on {}'.format("travel-sample")
#     sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, "travel-sample"),
#                             password=password,
#                             timeout=SDK_TIMEOUT)
#     query = N1QLQuery(n1ql_query)
#     sdk_client.n1ql_query(query)
# 
#     # Runing Query tests
#     log_info("Running Query tests")
# 
#     cmd = [
#            "{}/testsuites/CBLTester/CBL_Functional_tests/SuiteSetup_FunctionalTests".format(os.getcwd()),
#            "--timeout 1800", "--liteserv-version={}".format(upgraded_liteserv_version),
#            "--liteserv-host={}".format(liteserv_host), "--liteserv-port=8080",
#            "--sync-gateway-version={}".format(sg_version), "--mode=cc", "--server-version={}".format(server_version),
#            "--liteserv-platform={}".format(liteserv_platform), "--create-db-per-suite=cbl-test"
#            ]
#     pytest.main([cmd])


    # Cleaning the database , tearing down
    db.deleteDB(cbl_db) 