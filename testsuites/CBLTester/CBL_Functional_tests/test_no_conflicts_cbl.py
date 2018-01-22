import pytest
import time
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords import document, attachment
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from CBLClient.Authenticator import Authenticator
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf

def start_sg_accel(c, sg_conf):
    status = c.sg_accels[0].start(config=sg_conf)
    print "starting sg accel...."
    assert status == 0, "sync_gateway accel did not start"

@pytest.mark.sanity
@pytest.mark.listener
def test_no_conflicts_enabled(params_from_base_test_setup):
    """
        @summary:
        1. Enable allow_conflicts = true in SG config or do not set allow_conflicts
        2. Create docs on CBL.
        3. Update the doc few times.
        4. Do push replication to SG
        5. Create conflict on SG
        6. Do pull replication to CBL.
        7. Check the revision list for the doc
    """
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["ABC"]
    db = Database(base_url)

    if sync_gateway_version < "2.0" or no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_no_conflicts", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)

    for doc in sg_docs["rows"]:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 1),
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 5),
])
def test_no_conflicts_enabled_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Enable allow_conflicts = false in SG config and specified revs_limit
        2. Add a few docs through CBL.
        3. Update the doc few times in CBL.
        4. Do push replication to Sg with continous replication
        5. Update docs in CBL again few more times which can cross the revs_limit
        6. Check the revision list for the doc
    """
    # source_db = None
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]

    channels = ["no-conflicts-cbl"]
    db = Database(base_url)

    if not no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after adding revs_limit  with no conflicts mode "

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    cbl_docids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_docids)
    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit + 5):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    for doc in sg_docs:
        if no_conflicts_enabled:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert he.value.message.startswith('409 Client Error: Conflict for url:')
        else:
            conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                    auth=session)
            assert conflicted_rev["rev"] == "2-foo"

    # 5. Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=session, channels=channels)

    # 7. Get number of revisions and verify number of revisions should be same revs_limit
    # 8. Verify previous revisions does not exist
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 10)
])
def test_no_conflicts_update_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Have sg config with allow conflicts with some revs_limit
        2. Create docs in CBL
        3. Update docs in CBL and also update docs through SG with number of times more than revs_limit
        4. Change the revs_limit less than actual revs limit
        5. Restart sg
        6. update doc 1 more time.
        7. Verify revs limit is maintained with new modified revs_limit

    """
    # source_db = None
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]

    num_of_docs = 10
    channels = ["no-conflicts-cbl"]
    reduced_revs_limit = revs_limit - 3
    db = Database(base_url)

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after adding revs_limit  with no conflicts mode "

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    # Get cbl docs
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    log_info("replicator status is {} ".format(replicator.status(repl)))
    time.sleep(1)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    for doc in sg_docs:
        if no_conflicts_enabled:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert he.value.message.startswith('409 Client Error: Conflict for url:')
        else:
            conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                    auth=session)
            assert conflicted_rev["rev"] == "2-foo"

    # Update the docs few times
    # TODO : update docs by SG until this issue is fixed https://github.com/couchbase/couchbase-lite-core/issues/331
    # once issue is fixed, replace with update cbl docs
    # have for loop half the tiem of expected
    # for i in xrange((revs_limit + 5) / 2):
    for i in xrange(revs_limit + 5):
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                              auth=session, channels=channels)
        db.update_bulk_docs(cbl_db)

    # Get cbl docs
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    # Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"

    #  Modify the revs_limit less than actual revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', reduced_revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 2 with no conflicts mode"

    # Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=session, channels=channels)

    # Get number of revisions and verify number of revisions should be same revs_limit
    # Verify previous revisions does not exist
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == reduced_revs_limit, "Number of revisions in history is not equal to revs_limit set in sg config"
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 10),
    ('sync_gateway_revs_conflict_configurable', 1000, 5)
])
def test_migrate_conflicts_to_noConflicts_CBL(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Start SG 1.5.0 without allow_conflicts set and revs_limit set.
        2. Create docs in CBL
        3. Update the doc few times in CBL.
        4. Do push replication with one shot
        5. Create a conflicts in SG
        6. Now enable allow_conflicts = false in SG config
        7. Check the revision list for the doc and the active revision
        8. updats docs in CBL
        9. Do push replication with one shot again
        10. Create conflict on SG
        11. Verify conflicts cannot be created in SG
    """
    # source_db = None
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]

    num_of_docs = 10
    channels = ["no-conflicts-cbl"]
    db = Database(base_url)
    if revs_limit is None:
        revs_limit = 1000

    if no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    # TODO : update docs by SG until this issue is fixed https://github.com/couchbase/couchbase-lite-core/issues/331
    # once issue is fixed, replace with update cbl docs
    # Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)
    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    # Create a conflicts and verify it is successful.
    for doc in sg_docs:
        print "doc in migrat conflict ", doc
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                auth=session)
        assert conflicted_rev["rev"] == "2-foo"

    # Enable allow_conflicts = false in SG config and 6. restart sg
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'no_conflicts_enabled', "True", property_name_check=False)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    # TODO : Can replace with cbl update doc once 331 issue fixed
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=session, channels=channels)

    # Create a conflict and verify conflict throws 409.
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="3-foo1",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # Update the docs few times
    # TODO : Uncomment this once 311 is fixed :total_updates = (revs_limit + 5) / 2
    total_updates = revs_limit + 5
    for i in xrange(total_updates):
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                              auth=session, channels=channels)
        db.update_bulk_docs(cbl_db)

    # Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"

    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 5),
    ('sync_gateway_revs_conflict_configurable', 1000, 500)
])
def test_cbl_no_conflicts_sgAccel_added(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in CBL
        3. Now add the sg accel
        4. Do push replicationt to sg.
        5. update docs in CBL
        6. Verify docs updated successfully.
    """
    # source_db = None
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]

    num_of_docs = 10
    channels = ["no-conflicts-cbl"]
    db = Database(base_url)

    if not no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is not enabled and does not work with sg < 2.0 , so skipping the test')

    if mode != "di":
        pytest.skip('--no-conflicts is not enabled or mode is not di, so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    c.sg_accels[0].stop()

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(username="autotest", password="password", authentication_type="basic")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)

    # 1. Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit  with no conflicts mode"

    with ThreadPoolExecutor(max_workers=1) as tpe:
        wait_until_replicator_completes = tpe.submit(
            replicator.wait_until_replicator_idle,
            repl=repl
        )

        start_sg_accel_task = tpe.submit(
            start_sg_accel,
            c=c,
            sg_config=sg_config
        )
        wait_until_replicator_completes.result()
        start_sg_accel_task.result()
    time.sleep(1)  # needs some sleep time to do http call after multithreading
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    print "sg docs after getting all docs ", sg_docs

    # TODO : update docs by SG until this issue is fixed https://github.com/couchbase/couchbase-lite-core/issues/331
    # once issue is fixed, replace with update cbl docs
    # Update the docs few times
    for i in xrange(revs_limit):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=session, channels=channels)
    assert len(update_sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    # Create a conflicts and verify it throws conflict error
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo1",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # TODO: Test this : update docs through CBL and verify it throws conflict error
    db.update_bulk_docs(database=cbl_db, number_of_updates=3)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo1",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    ('listener_tests/listener_tests_no_conflicts', 100, 10),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_sg_CBL_updates_concurrently(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in SG in one thread, update docs in CBL in another thread -> will create CBL DB out of sync
        3. Now do sync dB of SG
    """
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["no-conflicts-channel"]
    db = Database(base_url)

    if sync_gateway_version < "2.0":
        pytest.skip('Does not work with sg < 2.0 , so skipping the test')

    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "CBL updated docs are ", cbl_docs
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    # TODO : Uncomment after the issue https://github.com/couchbase/couchbase-lite-core/issues/331 is fixed
    # replicator.start(repl)
    # wait_until_replicator_idle(replicator, repl)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    # sg_docs = sg_docs["rows"]
    # print("sg docs after replication is ", sg_docs)
    db.update_bulk_docs(database=cbl_db, number_of_updates=3)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "CBL updated docs and replication is are ", cbl_docs
    # Update the same documents concurrently from a sync gateway client and and CBL client
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_sg_task = tpe.submit(
            sg_client.update_docs,
            url=sg_url,
            db=sg_db,
            docs=sg_docs,
            number_updates=number_of_updates,
            auth=session
        )

        update_from_cbl_task = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db,
            number_of_updates=number_of_updates
        )
        update_from_sg_task.result()
        update_from_cbl_task.result()
    
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    
    sg_docs = sg_docs["rows"]
    assert len(sg_docs) == num_of_docs, "Did not have expected number of docs"
    if no_conflicts_enabled:
        for doc in sg_docs:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert he.value.message.startswith('409 Client Error: Conflict for url:')
    else:
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                auth=session)
        assert not he.value.message.startswith('409 Client Error: Conflict for url:')
        assert conflicted_rev["rev"] == "2-foo"
    db.deleteDB(cbl_db)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2),
    # ('listener_tests/listener_tests_no_conflicts', 100),
    # ('listener_tests/listener_tests_no_conflicts', 1000)
])
def test_multiple_cbls_updates_concurrently_with_push(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in SG in one thread, update docs in CBL in another thread -> will create CBL DB out of sync
        3. Now do sync dB of SG

    """

    sg_db = "db"
    cbl_db_name1 = "cbl_db1"
    cbl_db_name2 = "cbl_db2"
    cbl_db_name3 = "cbl_db3"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["no-conflicts-channel"]

    db = Database(base_url)

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]
    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL databases
    cbl_db1 = db.create(cbl_db_name1)
    cbl_db2 = db.create(cbl_db_name2)
    cbl_db3 = db.create(cbl_db_name3)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db1, channels=channels)
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db2, channels=channels)
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db3, channels=channels)

    cbl_doc_ids = db.getDocIds(cbl_db1)
    print "doc ids are ", cbl_doc_ids
    cbl_docs = db.getDocuments(cbl_db1, cbl_doc_ids)
    print "CBL updated docs are ", cbl_docs
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Replicate to CBL2
    replicator2 = Replication(base_url)
    replicator_authenticator = replicator2.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator2.configure(cbl_db1, target_db=cbl_db2, continuous=True, channels=channels)
    repl = replicator2.create(repl_config)
    replicator2.start(repl)
    replicator2.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db2)
    print "doc ids are ", cbl_doc_ids
    cbl_docs = db.getDocuments(cbl_db2, cbl_doc_ids)
    print "CBL2 replicated  docs are ", cbl_docs

    # Replicate to CBL3
    repl_config = replicator2.configure(cbl_db1, target_db=cbl_db3, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl3 = replicator2.create(repl_config)
    replicator2.start(repl3)
    db.update_bulk_docs(database=cbl_db1, number_of_updates=1)
    db.update_bulk_docs(database=cbl_db2, number_of_updates=1)
    db.update_bulk_docs(database=cbl_db3, number_of_updates=1)
    replicator2.wait_until_replicator_idle(repl3)
    cbl_doc_ids = db.getDocIds(cbl_db2)
    print "doc ids are ", cbl_doc_ids
    cbl_docs = db.getDocuments(cbl_db2, cbl_doc_ids)
    print "CBL3 replicated  docs are ", cbl_docs
    # Update the same documents concurrently from a sync gateway client and and CBL client

    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_cbl_task1 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db1,
            number_of_updates=number_of_updates
        )
        update_from_cbl_task2 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db2,
            number_of_updates=number_of_updates
        )
        update_from_cbl_task3 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db3,
            number_of_updates=number_of_updates
        )
        update_from_cbl_task1.result()
        update_from_cbl_task2.result()
        update_from_cbl_task3.result()

    replicator2.wait_until_replicator_idle(repl)
    replicator2.stop(repl)
    replicator2.wait_until_replicator_idle(repl3)
    replicator2.stop(repl3)
    # Replicate to Sync-gateway
    repl_config = replicator2.configure(cbl_db3, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator2.create(repl_config)
    process_replicator(replicator2, repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    cbl_doc_ids = db.getDocIds(cbl_db3)
    assert len(sg_docs) == len(cbl_doc_ids)
    sg_ids = [row["id"] for row in sg_docs["rows"]]
    for doc in cbl_doc_ids:
        assert doc in sg_ids, "cbl db3 docs did not get replicated to sync gateway"

    if no_conflicts_enabled:
        for doc in sg_docs["rows"]:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert he.value.message.startswith('409 Client Error: Conflict for url:')

    db.deleteDB(cbl_db1)
    db.deleteDB(cbl_db2)
    db.deleteDB(cbl_db3)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2),
    # ('listener_tests/listener_tests_no_conflicts', 100),
    # ('listener_tests/listener_tests_no_conflicts', 1000)
])
def test_multiple_cbls_updates_concurrently_with_pull(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in SG.
        2. Pull replication to 3 CBLs
        3. update docs in SG and all 3 CBL.
        4. Push replication to CBLs
        5. Verify docs can resolve conflicts and
        should able to replicate docs to CBL
        6. Update docs through all 3 CBLs
        7. Verify docs can be updated
        TODO : Fails due to the issue https://github.com/couchbase/couchbase-lite-ios/issues/2009
        Add verification of sync-gateway
    """

    sg_db = "db"
    cbl_db_name1 = "cbl_db1"
    cbl_db_name2 = "cbl_db2"
    cbl_db_name3 = "cbl_db3"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    num_of_docs = 10
    channels = ["no-conflicts-channel"]

    db = Database(base_url)
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    # sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
    #                               attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # Create CBL databases
    """cbl_db1 = db.create(cbl_db_name1)
    cbl_db2 = db.create(cbl_db_name2)
    cbl_db3 = db.create(cbl_db_name3)
    """
    cbl_db1 = db. deleteDBIfExistsCreateNew(cbl_db_name1)
    cbl_db2 = db. deleteDBIfExistsCreateNew(cbl_db_name2)
    cbl_db3 = db. deleteDBIfExistsCreateNew(cbl_db_name3)

    # Replicate to all 3 CBLs
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl1 = replicator.configure_and_replicate(cbl_db1, target_url=sg_blip_url, replication_type="pull", continuous=True,
                                               replicator_authenticator=replicator_authenticator)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    assert len(cbl_doc_ids1) == len(sg_docs)

    repl2 = replicator.configure_and_replicate(cbl_db2, target_url=sg_blip_url, replication_type="pull", continuous=True,
                                               replicator_authenticator=replicator_authenticator)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    assert len(cbl_doc_ids2) == len(sg_docs)

    repl3 = replicator.configure_and_replicate(cbl_db3, target_url=sg_blip_url, replication_type="pull", continuous=True,
                                               replicator_authenticator=replicator_authenticator)
    cbl_doc_ids3 = db.getDocIds(cbl_db2)
    assert len(cbl_doc_ids3) == len(sg_docs)

    # Update the same documents concurrently from a sync gateway client and and CBL client
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_cbl_task1 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db1,
            number_of_updates=number_of_updates
        )
        update_from_cbl_task2 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db2,
            number_of_updates=number_of_updates
        )
        update_from_cbl_task3 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db3,
            number_of_updates=number_of_updates
        )
        update_from_sg_task = tpe.submit(
            sg_client.update_docs,
            url=sg_url,
            db=sg_db,
            docs=sg_docs,
            number_updates=number_of_updates,
            auth=session
        )
        update_from_cbl_task1.result()
        update_from_cbl_task2.result()
        update_from_cbl_task3.result()
        update_from_sg_task.result()

    replicator.wait_until_replicator_idle(repl1)
    print "replicator 1 error is", replicator.getError(repl1)
    replicator.stop(repl1)
    replicator.wait_until_replicator_idle(repl2)
    print "replicator 2 error is", replicator.getError(repl2)
    replicator.stop(repl2)
    replicator.wait_until_replicator_idle(repl3)
    print "replicator 3 error is", replicator.getError(repl3)
    replicator.stop(repl3)

    # Replicate to Sync-gateway to CBLs
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db1, target_url=sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl1 = replicator.create(repl_config)
    replicate_update_cbl_docs(replicator, db, cbl_db1, repl1)

    repl_config = replicator.configure(cbl_db2, target_url=sg_blip_url, continuous=True,
                                       channels=channels, replicator_authenticator=replicator_authenticator)
    repl2 = replicator.create(repl_config)
    # replicate_update_cbl_docs(replicator, db, cbl_db2, repl2)

    repl_config = replicator.configure(cbl_db3, target_url=sg_blip_url, continuous=True,
                                       channels=channels, replicator_authenticator=replicator_authenticator)
    repl3 = replicator.create(repl_config)
    replicate_update_cbl_docs(replicator, db, cbl_db3, repl3)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates, add_attachments", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2, false),
    # ('listener_tests/listener_tests_no_conflicts', 10, 3 , true ),
    # ('listener_tests/listener_tests_no_conflicts', 1000)
])
def test_sg_cbl_updates_concurrently_with_push_pull(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates, add_attachments):
    """
        @summary:
        1. Create docs in SG.
        2. Pull replication to CBL
        3. update docs in SG and CBL.
        4. Push_pull replication to CBL.
        5. Verify docs can resolve conflicts and
        should able to replicate docs to CBL
        6. Update docs through in CBL
        7. Verify docs got replicated to sg with CBL updates
        TODO : Fails due to the issue https://github.com/couchbase/couchbase-lite-ios/issues/2009
        Add verification of sync-gateway
    """
    
    sg_db = "db"
    cbl_db_name1 = "cbl_db1"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    channels = ["replication"]
    
    db = Database(base_url)
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    if add_attachments:
        sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                       attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    else:
        sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # Create CBL databases
    # cbl_db1 = db.create(cbl_db_name1)
    cbl_db1 = db. deleteDBIfExistsCreateNew(cbl_db_name1)

    # Replicate to all CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(cbl_db1, target_url=sg_blip_url, replication_type="pull", continuous=True,
                                               replicator_authenticator=replicator_authenticator)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    assert len(cbl_doc_ids1) == len(sg_docs)

    # Update the same documents concurrently from a sync gateway client and and CBL client
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_cbl_task1 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db1,
            number_of_updates=number_of_updates
        )
        update_from_sg_task = tpe.submit(
            sg_client.update_docs,
            url=sg_url,
            db=sg_db,
            docs=sg_docs,
            number_updates=number_of_updates,
            auth=session
        )
        update_from_cbl_task1.result()
        update_from_sg_task.result()
    
    replicator.wait_until_replicator_idle(repl1)
    replicator.stop(repl1)
    
    # Replicate to Sync-gateway to CBLs
    replicator = Replication(base_url)
    repl_config = replicator.configure(cbl_db1, target_url=sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl1 = replicator.create(repl_config)
    replicate_update_cbl_docs(replicator, db, cbl_db1, repl1)
    verify_sg_docs_after_replication(no_conflicts_enabled, sg_client, sg_url, sg_db, session)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    # ('listener_tests/listener_tests_no_conflicts', 100, 10),
    # ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_CBL_push_without_pull(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in SG.
        2. Pull replication to CBL
        3. update docs in SG .
        4. Update docs in CBL(without doing pull).
        5. Push replication.
        TODO : Bugs need to resolved to run this test : https://github.com/couchbase/couchbase-lite-ios/issues/2009
        https://github.com/couchbase/couchbase-lite-ios/issues/2010

    """
    # base_url = "http://192.168.0.109:8989"
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    num_of_docs = 10
    channels = ["no-conflicts-channel"]
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    # Modify sync-gateway config to use no-conflicts config
    db = Database(base_url)
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                   attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    # sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # 2. Pull replication to CBL
    cbl_db = db.create(cbl_db_name)
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="pull", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    
    # 3. Update the docs few times
    for i in xrange(number_of_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=session, channels=channels)
        print "updated sg docs are ", update_sg_docs
    
    # 4. Update docs in CBL(without pull replication from SG)
    db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "CBL updated docs ", cbl_docs

    # 5. Push replication to SG
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    repl_change_listener = replicator.addChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    changes = replicator.getChangesChangeListener(repl_change_listener)
    repl_error = replicator.getError(repl)
    replicator.stop(repl)
    print "replicator changes", changes
    # 6 Get sg docs
    sg_conflict_resolved_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)

    sg_docs = sg_conflict_resolved_docs["rows"]

    if no_conflicts_enabled:
        assert "Domain=LiteCore Code=35 \"Document update conflict\"" in repl_error
        for doc in sg_docs:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert he.value.message.startswith('409 Client Error: Conflict for url:')
    else:
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                auth=session)
        assert not he.value.message.startswith('409 Client Error: Conflict for url:')
        assert conflicted_rev["rev"] == "2-foo"
    db.deleteDB(cbl_db)


def process_replicator(replicator, repl, repl_change_listener=None):

    max_times = 50
    count = 0
    replicator.start(repl)
    # Sleep until replicator completely processed
    while(replicator.getActivitylevel(repl) != 3 and count < max_times):
        print "sleeping... actvity level is", replicator.getActivitylevel(repl)
        time.sleep(0.5)
        count += 1

    if repl_change_listener is not None:
        changes = replicator.getChangesChangeListener(repl_change_listener)
        print "Changes are ", changes
    print "replicator error is ", replicator.getError(repl)
    replicator.stop(repl)


def replicate_update_cbl_docs(replicator, db, cbl_db, repl):
    change_listener = replicator.addChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    # update CBL docs
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == 3, "updates-cbl did not get updated"

    replicator.wait_until_replicator_idle(repl)
    changes = replicator.getChangesChangeListener(change_listener)
    print "changes in replicator is ", changes
    error = replicator.getError(repl)
    print "Error1 in replicator is ", error
    replicator.stop(repl)
    print "cbl docs are in replicate_update_cbl_docs", cbl_db_docs
    return cbl_db_docs
    

def verify_sg_docs_after_replication(no_conflicts_enabled, sg_client, sg_url, sg_db, session):
    if no_conflicts_enabled:
        print "should do verification "
        # TODO : should change the verification once below issue is fixed
        # https://github.com/couchbase/couchbase-lite-core/issues/331
        # assert "Domain=WebSocket Code=409 \"rejected by proposeChanges\"" in error
    else:
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
        for doc in sg_docs["rows"]:
            doc_body = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
            assert doc_body["updates-cbl"] > 0

    # if no conflicts enabled, it should throw an error while replication happens to SG. It is not throwing error now
    # TODO : https://github.com/couchbase/couchbase-lite-ios/issues/2010




