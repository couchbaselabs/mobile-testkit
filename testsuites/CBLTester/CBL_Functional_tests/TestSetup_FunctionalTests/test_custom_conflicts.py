import pytest

from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from requests.exceptions import HTTPError

from testsuites.CBLTester.CBL_Functional_tests.TestSetup_FunctionalTests.test_delta_sync import property_updater


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.custom_conflict
@pytest.mark.replication
@pytest.mark.parametrize("replicator_type", [
    "pull",
    "push",
    "push_pull"
])
def test_local_win_custom_conflicts(params_from_base_test_setup, replicator_type):
    """
    @summary: resolve conflicts as per local doc
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config  = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if liteserv_version < "2.6.0":
        pytest.skip('test does not work with liteserv_version < 2.6.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "local_win_conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    log_info("Using SG ur: {}".format(sg_admin_url))
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=False, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="push_pull")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]

    # creating conflict for docs on SG
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2, property_updater=property_updater)

    # creating conflict for docs on CBL
    doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id in cbl_docs:
        for _ in range(2):
            log_info("Updating CBL Doc - {}".format(doc_id))
            data = cbl_docs[doc_id]
            data = property_updater(data)
            db.updateDocument(cbl_db, doc_id=doc_id, data=data)

    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type=replicator_type, conflict_resolver="local_wins")
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"
