import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.testkit import cluster
from keywords import document

@pytest.fixture(scope="function")
def setup_teardown_test(params_from_base_test_setup):
    cbl_db_name = "cbl_db"
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    log_info("Creating db")
    cbl_db = db.create(cbl_db_name, db_config)

    yield{
        "db": db,
        "cbl_db": cbl_db,
        "cbl_db_name": cbl_db_name
    }

    log_info("Deleting the db")
    db.deleteDB(cbl_db)


@pytest.mark.replication
def test_replication_heartbeat(params_from_base_test_setup):
    """
        @summary:
        This test to verify heartbeat keeps websocket connection alive
        1. create cbl db and add 10 docs on CBL
        2. create 15 docs on SGW
        3. create a push_pull continuous replicator, start replication
        4. verify docs are all replicated
        5. sleep for 90 seconds, then create some docs on cbl
        6. verify if docs are replicated to sync gateway
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    db_config = params_from_base_test_setup["db_config"]

    # Reset nginx with shorter keep_alive frequency config
    from libraries.provision.install_nginx import install_nginx
    print(cluster_config)
    install_nginx(cluster_config, True)

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_db = "db"
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, username)
    auth_session = cookie, session
    sync_cookie = "{}={}".format(cookie, session)

    session_header = {"Cookie": sync_cookie}

    # replicator = Replication(base_url)
    # repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, headers=session_header)

    heartbeat = '15'
    # 1. create cbl db and add 10 docs on CBL
    cbl_db_name = "heartbeat-" + str(time.time())
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(db=cbl_db, number=10, id_prefix="cbl_batch_1", channels=channels)

    # # 2. create 15 docs on SGW
    # sg_client.add_docs(url=sg_url, db=sg_db, number=15, id_prefix="sg_batch_1", channels=channels, auth=auth_session)

    # 3. create a push_pull continuous replicator, start replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False, headers=session_header)
    repl = replicator.create(repl_config)

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    # 4. verify docs are all replicated
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    log_info("count of sg_docs = {}".format(len(sg_docs)))
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    log_info("count of cbl_db_docs = {}".format(len(cbl_db_docs)))
    assert len(sg_docs) == len(cbl_db_docs), "docs are not replicated correctly"

    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=3, channels=channels)
    session = cookie, session
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    # 5. sleep for 90 seconds, then create some docs on cbl
    time.sleep(90)
    replicator.start(repl)
    db.create_bulk_docs(db=cbl_db, number=9, id_prefix="cbl_batch_2", channels=channels)
    replicator.wait_until_replicator_idle(repl)
    # 6. wait for 20 seconds, verify if docs are replicated to sync gateway
    time.sleep(10)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    log_info("count of sg_docs = {}".format(len(sg_docs)))
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    log_info("count of cbl_db_docs = {}".format(len(cbl_db_docs)))
    db.create_bulk_docs(db=cbl_db, number=5, id_prefix="cbl_batch_1", channels=channels)

    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    assert len(sg_docs) == len(cbl_db_docs)
