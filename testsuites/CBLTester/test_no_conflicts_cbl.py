import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from CBLClient.Utils import Release
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from libraries.testkit import cluster


@pytest.mark.sanity
@pytest.mark.listener
def test_no_conflicts_enabled(setup_client_syncgateway_test):
    """
        @summary: 
    """
    # source_db = None
    base_url = "http://192.168.0.109:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_blip_url = sg_admin_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_no_conflicts", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)
    log_info("Database is {}".format(cbl_db))
    
    # Create bulk doc json
    bulk_doc = {
        "no_conflicts_0": {
            "c": "d",
            "e": "f"
        },
        "no_conflicts_1": {
            "g": "h",
            "i": "j"
        },
        "no_conflicts_2": {
            "2": "3",
            "4": "5"
        },
        "no_conflicts_3": {
            "g": "h",
            "i": "j"
        }
    }

    db.addDocuments(cbl_db, bulk_doc)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=["ABC"])
    session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    docs = sg_client.add_docs(
        url=sg_url,
        db=sg_db,
        number=10,
        id_prefix="sg_doc",
        channels=["ABC"],
        auth=session
    )
    # Start and stop continuous replication
    replicator = Replication(base_url)
    channels_sg = "ABC"
    repl = replicator.configure_replication(cbl_db, sg_blip_url, continuous=True, channels=channels_sg)
    replicator.start_replication(repl)
    log_info("replication activity level after starting replication is {}".format(replicator.replication_get_activitylevel(repl)))
    
    time.sleep(1)
    """sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    log_info("sg doc full details >><<{}".format(sg_docs["rows"]))
    for doc in sg_docs:
        log_info("doc full details >><<{}".format(doc["rows"]))
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')"""
    log_info("replication activity level before sleep is {}".format(replicator.replication_get_activitylevel(repl)))
    log_info("replication status before sleep is  {}".format(replicator.replication_status(repl)))
    replicator.stop_replication(repl)
    cbl_docs = db.getDocuments(cbl_db)
    log_info("cbs docs are >><< {}".format(cbl_docs))
    """sg_docs = sg_client.add_docs(
        url=sg_admin_url,
        db=sg_db,
        number=5,
        id_prefix="no_conflicts"
    )
    log_info("replication activity level before sleep is {}".format(replicator.replication_get_activitylevel(repl)))
    log_info("replication status before sleep is  {}".format(replicator.replication_status(repl)))
    
    time.sleep(1)
    log_info("replication ob is {}".format(replicator.replication_status(repl)))
    log_info("replication progress is {}".format(replicator.replication_get_progress(repl)))
    log_info("replication activity level is {}".format(replicator.replication_get_activitylevel(repl)))
    log_info("replication status after replication done is  {}".format(replicator.replication_status(repl)))
    time.sleep(1)
    replicator.stop_replication(repl)
    
    all_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    # log_info("all docs are {}".format(all_docs))
    log_info("replication activity level after stop is {}".format(replicator.replication_get_activitylevel(repl)))
    # sg_client.delete_docs(url=sg_admin_url, db=sg_db, docs=sg_docs) """