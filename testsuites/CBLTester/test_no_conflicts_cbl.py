import pytest
import time
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

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
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf


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
    # source_db = None
    base_url = "http://10.17.1.161:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    num_of_docs = 10
    channels = ["ABC"]

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
    repl = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    replicator.start(repl)
    # while replicator.get_completed(repl) != num_of_docs:
    time.sleep(4)
    replicator.stop(repl)
    print "replication completed info ", replicator.getCompleted(repl)
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
    base_url = "http://10.17.1.161:8989"
    db = Database(base_url)

    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    channels = ["no-conflicts-cbl"]

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
    time.sleep(2)
    # while replicator.get_completed(repl) != num_of_docs:
    """change_listener = replicator.add_change_listener(repl)
    changes = replicator.get_changes_changelistener(change_listener, 1)
    log_info("changes is {}".format(changes)) 
    
    print "replication completed info ", replicator.get_completed(repl)
    print "replication total info ", replicator.get_total(repl)
    time.sleep(4)
    print "replication error info ", replicator.get_error(repl)"""
    replicator.stop(repl)
    
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    cbl_docids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_docids)
    log_info("cbl docs are {}".format(cbl_docs))
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
    base_url = "http://192.168.0.103:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    
    num_of_docs = 10
    channels = ["no-conflicts-cbl"]
    reduced_revs_limit = revs_limit - 3

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
    log_info("CBL docs are sri -- {}".format(cbl_docs))

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
    # ('sync_gateway_revs_conflict_configurable', 100, 10),
    # ('sync_gateway_revs_conflict_configurable', 1000, 5)
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
    base_url = "http://10.17.3.55:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    
    num_of_docs = 10
    channels = ["no-conflicts-cbl"]
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
    log_info("replicator status is {} ".format(replicator.status(repl)))
    # Sleep until replicator completely processed
    # while replicator.get_completed < replicator.get_total:
    time.sleep(1)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    print " sg docs after replication is ", sg_docs
    
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
    base_url = "http://10.17.3.55:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    
    num_of_docs = 10
    channels = ["no-conflicts-cbl"]

    # if not no_conflicts_enabled or sync_gateway_version < "2.0":
    #    pytest.skip('--no-conflicts is not enabled and does not work with sg < 2.0 , so skipping the test')
    
    if mode != "di":
        pytest.skip('--no-conflicts is not enabled or mode is not di, so skipping the test')
    
    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    # c.sg_accels[0].stop()

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
    
    t = Thread(target=wait_until_replicator_idle, args=(replicator, repl))
    t1 = Thread(target=start_sg_accel, args=(c, sg_config))
    t.start()
    t1.start()
    time.sleep(1) # needs some sleep time to do http call after multithreading
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    print "sg docs after getting all docs ", sg_docs
    
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

    # Create a conflicts and verify it throws conflict error
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo1",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # update docs through CBL and verify it throws conflict error


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    # ('listener_tests/listener_tests_no_conflicts', 100),
    # ('listener_tests/listener_tests_no_conflicts', 1000)
])
def test_sg_CBL_updates_concurrently(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in SG in one thread, update docs in CBL in another thread -> will create CBL DB out of sync
        3. Now do sync dB of SG
    """
    base_url = "http://10.17.3.55:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    num_of_docs = 10
    channels = ["no-conflicts-channel"]

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    """print "updating cbl docs 1st time"
    db.update_bulk_docs(cbl_db)
    print "updating cbl docs 2nd time"
    db.update_bulk_docs(cbl_db)
    print "updating cbl docs 3rd time"
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    """
    cbl_doc_ids = db.getDocIds(cbl_db)
    print "doc ids are ", cbl_doc_ids
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
    replicator.start(repl)
    wait_until_replicator_idle(replicator, repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    print("sg docs after replication is ", sg_docs)
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)
    wait_until_replicator_idle(replicator, repl)
    print("sg docs after replication is after CBL update is ", sg_docs)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    print "CBL updated docs and replication is are ", cbl_docs
    # Update the same documents concurrently from a sync gateway client and and CBL client
    """
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
    
    wait_until_replicator_idle(replicator, repl)
    replicator.stop(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    
    for doc in sg_docs["rows"]:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')
    """
    db.deleteDB(cbl_db)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    # ('listener_tests/listener_tests_no_conflicts', 100),
    # ('listener_tests/listener_tests_no_conflicts', 1000)
])
def test_multiple_cbls_updates_concurrently(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in SG in one thread, update docs in CBL in another thread -> will create CBL DB out of sync
        3. Now do sync dB of SG
    """
    base_url = "http://10.17.3.55:8989"
    db = Database(base_url)
    
    sg_db = "db"
    cbl_db_name = "cbl_db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    num_of_docs = 10
    channels = ["no-conflicts-channel"]

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create CBL database
    cbl_db = db.create(cbl_db_name)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    """print "updating cbl docs 1st time"
    db.update_bulk_docs(cbl_db)
    print "updating cbl docs 2nd time"
    db.update_bulk_docs(cbl_db)
    print "updating cbl docs 3rd time"
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)
    """
    cbl_doc_ids = db.getDocIds(cbl_db)
    print "doc ids are ", cbl_doc_ids
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
    replicator.start(repl)
    wait_until_replicator_idle(replicator, repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    print "sg docs after replication is ", sg_docs
    # Update the same documents concurrently from a sync gateway client and and CBL client
    
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
    
    wait_until_replicator_idle(replicator, repl)
    replicator.stop(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    
    for doc in sg_docs["rows"]:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                   auth=session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')
def process_replicator(replicator, repl):
    max_times = 15
    count = 0
    replicator.start(repl)
    # Sleep until replicator completely processed
    while(replicator.getActivitylevel(repl) != 3 and count < max_times):
        print "sleeping... actvity level is", replicator.getActivitylevel(repl)
        time.sleep(0.5)
        count += 1
    replicator.stop(repl)


def wait_until_replicator_idle(replicator, repl):
    """max_times = 50
    count = 0
    # Sleep until replicator completely processed
    while(replicator.getActivitylevel(repl) != 3 and count < max_times):
        print "sleeping... actvity level is", replicator.getActivitylevel(repl)
        time.sleep(0.5)
        count += 1
    """
    time.sleep(5)

def start_sg_accel(c, sg_conf):
    status = c.sg_accels[0].start(config=sg_conf)
    print "starting sg accel...."
    assert status == 0, "sync_gateway accel did not start"
