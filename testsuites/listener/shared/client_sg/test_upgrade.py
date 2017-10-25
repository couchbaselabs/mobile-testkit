import pytest
import datetime

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RESULTS_DIR

@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.upgrade
def test_upgrade(setup_client_syncgateway_test):
    """
    1. install previous version of couchbase lite.
    2. Create docs in the lite.
    3. upgrade to latest version of couchbase lite.
    4. Verfiy docs still exits and accessible
    """
    sg_db = "db"
    ls_db = "ls_db"
    channels = ["auto"]

    num_docs = 1000

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]
    liteserv = setup_client_syncgateway_test["liteserv"]
    device_enabled = setup_client_syncgateway_test["device_enabled"]
    liteserv_platform = setup_client_syncgateway_test["liteserv_platform"]
    liteserv_version = setup_client_syncgateway_test["liteserv_version"]
    
    if liteserv_platform.lower() == "android":
        pytest.skip('upgrade lite serv app does not work on Android, so skipping the test')
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))
    test_name = "test_upgrade"

    log_info("Downloading LiteServ ...")
    # Download LiteServ with older version and test it
    liteserv.download_Version("1.4.0-3")
    
    # Install LiteServ
    if device_enabled and liteserv_platform == "ios":
        liteserv.stop()
        liteserv.install_device()
        ls_url = liteserv.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    else:
        liteserv.stop()
        liteserv.install()
        log_info("Listener going to start and launch,")
        ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    
    client = MobileRestClient()
    client.create_user(sg_one_admin, sg_db, "test", password="password", channels=channels)
    session = client.create_session(sg_one_admin, sg_db, "test")

    client.create_database(url=ls_url, name=ls_db)

    # Create 'num_docs' docs on LiteServ
    docs = client.add_docs(
        url=ls_url,
        db=ls_db,
        number=num_docs,
        id_prefix="seeded_doc",
        generator="four_k",
        channels=channels
    )
    assert len(docs) == num_docs
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs, timeout=240)

    # Now download with latest  version and verify docs still exits
    liteserv.download_Version(liteserv_version)
    
    # Install LiteServ
    if device_enabled and liteserv_platform == "ios":
        liteserv.stop()
        liteserv.install_device()
        ls_url = liteserv.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    else:
        liteserv.stop()
        liteserv.install()
        log_info("Listener going to start and launch,")
        ls_url = liteserv.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now()))
    
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs, timeout=240)
