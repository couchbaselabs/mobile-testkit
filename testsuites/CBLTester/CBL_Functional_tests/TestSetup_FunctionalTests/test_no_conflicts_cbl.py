import pytest
import time

from concurrent.futures import ThreadPoolExecutor
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords import document, attachment
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf


def start_sg_accel(c, sg_conf):
    status = c.sg_accels[0].start(config=sg_conf)
    log_info("starting sg accel....")
    assert status == 0, "sync_gateway accel did not start"


@pytest.mark.sanity
@pytest.mark.ce_sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
def test_no_conflicts_enabled(params_from_base_test_setup):
    """
        @summary:
        1. Enable allow_conflicts = true in SG config or do not set allow_conflicts
        2. Create docs on CBL.
        3. Update the doc few times.
        4. Do push and pull  replication
        5. Wait until replicaiton is idle
        6. Create conflict on SG
        7. Verify conflict creation fails and throws error
    """
    sg_db = "db"
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
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    if sync_gateway_version < "2.0" or not no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_no_conflicts", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
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
        assert str(he.value).startswith('409 Client Error: Conflict for url:')


@pytest.mark.listener
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 1),
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 25)
])
def test_no_conflicts_enabled_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Enable allow_conflicts = false in SG config and specified revs_limit
        2. Add a few docs through CBL.
        3. Update the doc few times in CBL.
        4. Do push and pull  replication to Sg with continous replication
        5. Update docs in CBL again few more times which can cross the revs_limit
        6. Check the revision list for the doc
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["no-conflicts-cbl"]

    if not no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is not enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after adding revs_limit  with no conflicts mode "

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    time.sleep(2)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    # 3. Update the docs few times
    prev_revs = []
    for i in range(revs_limit + 5):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    for doc in sg_docs:
        if no_conflicts_enabled:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                       auth=session)
            assert str(he.value).startswith('409 Client Error: Conflict for url:')

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
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"


@pytest.mark.listener
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 25),
    ('sync_gateway_revs_conflict_configurable', 100, 35),
    ('sync_gateway_revs_conflict_configurable', 100, 50)
])
def test_no_conflicts_update_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Have sg config with allow conflicts with some revs_limit
        2. Create docs in CBL
        3. Start a continous Replicator to have SG load all the docs. Verify if the no. of docs are same in both SG and CBL.
        4. Update docs in CBL and also update docs through SG with number of times more than revs_limit. check the docs after replication become idle
        5. Change the revs_limit less than actual revs limit
        6. Restart sg
        7. update doc 1 more time and let replication become idle
        8. Verify revs limit is maintained with new modified revs_limit

    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["no-conflicts-cbl"]
    reduced_revs_limit = revs_limit - 3

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Modify the revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after adding revs_limit  with no conflicts mode "

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db, number_of_updates=4)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    log_info("replicator status is {} ".format(replicator.status(repl)))
    replicator.wait_until_replicator_idle(repl)
    time.sleep(2)  # Give some time to get update to sync-gateway
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "

    for doc in sg_docs:
        if no_conflicts_enabled:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                       auth=session)
            assert str(he.value).startswith('409 Client Error: Conflict for url:')

            time.sleep(1)
        else:
            conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                                    auth=session)
            assert conflicted_rev["rev"] == "2-2B"

    replicator.wait_until_replicator_idle(repl)
    # Update the docs few times
    for i in range(revs_limit + 5):
        db.update_bulk_docs(cbl_db)
        time.sleep(1)

    replicator.wait_until_replicator_idle(repl)
    # Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history does not match the revs_limit set in sg config"

    #  Modify the revs_limit less than actual revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', reduced_revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 2 with no conflicts mode"
    time.sleep(9)

    # Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=session, channels=channels)
    time.sleep(5)
    replicator.wait_until_replicator_idle(repl)
    # Get number of revisions and verify number of revisions should be same revs_limit
    # Verify previous revisions does not exist
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == reduced_revs_limit, "Number of revisions in history is not equal to revs_limit set in sg config"
    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 10),
    ('sync_gateway_revs_conflict_configurable', 500, 5)
])
def test_migrate_conflicts_to_noConflicts_CBL(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Start SG without allow_conflicts set and revs_limit set.
        2. Create docs in CBL
        3. Update the doc few times in CBL.
        4. Do push and pull replication with continuous
        5. Create a conflicts in SG
        6. Now enable allow_conflicts = false in SG config
        7. Check the revision list for the doc and the active revision
        8. update docs in CBL
        9. Do push and pull replication again
        10. Create conflict on SG
        11. Verify conflicts cannot be created in SG
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["no-conflicts-cbl"]
    if revs_limit is None:
        revs_limit = 1000

    if no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    for i in range(revs_limit):
        db.update_bulk_docs(cbl_db)
    replicator.wait_until_replicator_idle(repl)
    assert len(sg_docs) == num_of_docs, "SG docs docs count is not same as CBL docs count "
    # Create a conflicts and verify it is successful.
    for doc in sg_docs:
        log_info("Doc rev: {}".format(doc["value"]["rev"]))
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                                auth=session)
        assert conflicted_rev["rev"] == "2-2B"

    # Enable allow_conflicts = false in SG config and 6. restart sg
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'no_conflicts_enabled', "True", property_name_check=False)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    db.update_bulk_docs(cbl_db)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    # Create a conflict and verify conflict throws 409.
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="3-2B",
                                   auth=session)
        assert he.value.args[0].startswith('409 Client Error: Conflict for url:')

    total_updates = (revs_limit + 5) / 2
    for i in range(total_updates):
        try:
            sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                  auth=session, channels=channels)
        except HTTPError as he:
            if he.response.status_code == 409 and str(he).startswith('409 Client Error: Conflict for url:'):
                log_info(
                    'There is conflict error due to update docs in SG and CBL and replication happenng in backgroud, so continuing ...')
        db.update_bulk_docs(cbl_db)

    # Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 20),
    ('sync_gateway_revs_conflict_configurable', 100, 20),
    ('sync_gateway_revs_conflict_configurable', 10, 500)
])
def test_cbl_no_conflicts_sgAccel_added(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """
        @summary:
        1. Create docs in CBL
        2. update docs in CBL
        3. Now add the sg accel
        4. Do push and pull replication to sg.
        5. update docs in CBL
        6. Verify docs updated successfully.
        7. Create conflict and verify conflicts are not allowed after sg accel is added
    """
    # source_db = None
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["no-conflicts-cbl"]

    if not no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('It does not work with sg < 2.0 or conflicts is not enabled, so skipping the test')

    if mode != "di":
        pytest.skip('--no-conflicts is not enabled or mode is not di, so skipping the test')

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    c.sg_accels[0].stop()

    # Create bulk doc json and update docs in CBL
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    db.update_bulk_docs(cbl_db)
    db.update_bulk_docs(cbl_db)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(username="autotest", password="password", authentication_type="basic")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)

    # 1. Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit  with no conflicts mode"

    with ThreadPoolExecutor(max_workers=4) as tpe:
        wait_until_replicator_completes = tpe.submit(
            replicator.wait_until_replicator_idle,
            repl=repl,
            err_check=False
        )

        start_sg_accel_task = tpe.submit(
            start_sg_accel,
            c=c,
            sg_conf=sg_config
        )
        wait_until_replicator_completes.result()
        start_sg_accel_task.result()
    time.sleep(1)  # needs some sleep time to do http call after multithreading
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    for i in range(revs_limit):
        db.update_bulk_docs(cbl_db)

    replicator.wait_until_replicator_idle(repl)
    time.sleep(1)  # needs some sleep time to do http call after multithreading
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    # Create a conflicts and verify it throws conflict error
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo1",
                                   auth=session)
        assert he.value.args[0].startswith('409 Client Error: Conflict for url:')

    db.update_bulk_docs(database=cbl_db, number_of_updates=3)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo1",
                                   auth=session)
        assert he.value.args[0].startswith('409 Client Error: Conflict for url:')


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    ('listener_tests/listener_tests_no_conflicts', 100, 10),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_sg_CBL_updates_concurrently(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL
        2. Start replication with push pull and continuous true.
        3. Update docs in CBL.
        4. Wait until replication is idle.
        5. update docs in SG in one thread, update docs in CBL in another thread -> will create CBL DB out of sync
        6. Verify it throws 409 with no-conflicts mode or else it should create no-conflicts successfully.
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["no-conflicts-channel"]

    if sync_gateway_version < "2.0":
        pytest.skip('Does not work with sg < 2.0 , so skipping the test')

    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    else:
        sg_config = params_from_base_test_setup["sg_config"]

    # Reset cluster to clean the data
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    if sync_gateway_version >= "2.5.0":
        sg_client = MobileRestClient()
        expvars = sg_client.get_expvars(sg_admin_url)
        num_replications_active = expvars["syncgateway"]["per_db"][sg_db]["database"]["num_replications_active"]
        num_replications_total = expvars["syncgateway"]["per_db"][sg_db]["database"]["num_replications_total"]
        """if continuous:
            # num_pull_repl_active_continuous = expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_active_continuous"]
            num_pull_repl_total_continuous = expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_total_continuous"]
        else:
            num_pull_repl_active_one_shot = expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_active_one_shot"]
            num_pull_repl_total_one_shot = expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_total_one_shot"]
        """
    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts", db=cbl_db, channels=channels)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]

    db.update_bulk_docs(database=cbl_db, number_of_updates=3)
    replicator.wait_until_replicator_idle(repl)

    # Update the same documents concurrently from a sync gateway client and and CBL client
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    sg_docs = sg_docs["rows"]
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_sg_task = tpe.submit(
            sg_updateDocs,
            sg_client=sg_client,
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
    if sync_gateway_version >= "2.5.0":
        expvars = sg_client.get_expvars(sg_admin_url)
        assert expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_active_continuous"] == 1, "num_pull_repl_active_continuous did not incremented"
        assert num_replications_active < expvars["syncgateway"]["per_db"][sg_db]["database"]["num_replications_active"], "num_replications_active did not incremented"

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
            assert str(he.value).startswith('409 Client Error: Conflict for url:')

    else:
        for doc in sg_docs:
            conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-foo",
                                                    auth=session)
            assert conflicted_rev["rev"] == "2-foo"

    # If number of docs is 1000 or more, it needs more time to delete the database after replicator is stopped, so it needs some sleep time before
    # database gets deleted at teardown
    if num_of_docs >= 1000:
        time.sleep(3)

    if sync_gateway_version >= "2.5.0":
        expvars = sg_client.get_expvars(sg_admin_url)
        assert num_replications_total < expvars["syncgateway"]["per_db"][sg_db]["database"]["num_replications_total"], "num_replications_total did not incremented"
        assert expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_push"]["write_processing_time"] > 0, "write_processing_time  did not incremented"
        assert expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_push"]["propose_change_time"] > 0, "propose_change_time stats did not get incremented"
        assert expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_pull"]["num_pull_repl_total_continuous"] == 1, "num_pull_repl_total_continuous did not get incremented"


def sg_updateDocs(sg_client, url, db, docs, number_updates, auth):
    for doc in docs:
        count = 0
        while count < 10:
            try:
                sg_client.update_doc(url=url, db=db, doc_id=doc["id"], number_updates=number_updates, auth=auth)
                break
            except HTTPError as he:
                if (he.response.status_code == 409 and str(he).startswith('409 Client Error: Conflict for url:')):
                    log_info("retrying the doc to update again due to conflict issue ....")
                count = + 1


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2),
    ('listener_tests/listener_tests_no_conflicts', 100, 10),
    ('listener_tests/listener_tests_no_conflicts', 100, 50)
])
def test_multiple_cbls_updates_concurrently_with_push(params_from_base_test_setup, setup_customized_teardown_test, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in CBL DB1, DB2 , DB3 associated with its own channel.
        2. Replicate docs from CBL DB1 to DB2 with push pull and continous.
        3. Wait until replication is done.
        4. Replicate docs from CBL DB1 to DB3.
        5. Wait until replication is done with push pull and continous.
        6. update docs on CBL DB1, DB2, DB3.
        7. Now update docs concurrently on all 3 CBL DBs.
        8. Wait until replication is done.
        9. Replicate docs from CBL DB3 to sg with push pull and continous.
        10. Verify all docs replicated to sync-gateway.
        11. Verify no conflicts allowed when trying to create conflicts
    """

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
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
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]

    # Create bulk doc json
    db.create_bulk_docs(num_of_docs, "no-conflicts1", db=cbl_db1, channels=channels)
    db.create_bulk_docs(num_of_docs, "no-conflicts2", db=cbl_db2, channels=channels)
    db.create_bulk_docs(num_of_docs, "no-conflicts3", db=cbl_db3, channels=channels)

    cbl_doc_ids = db.getDocIds(cbl_db1)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # Replicate to CBL2
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db1, target_db=cbl_db2, continuous=True, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db2)

    # Replicate to CBL3
    repl_config = replicator.configure(cbl_db1, target_db=cbl_db3, continuous=True, replicator_authenticator=replicator_authenticator)
    repl3 = replicator.create(repl_config)
    replicator.start(repl3)
    db.update_bulk_docs(database=cbl_db1, number_of_updates=1)
    db.update_bulk_docs(database=cbl_db2, number_of_updates=1)
    db.update_bulk_docs(database=cbl_db3, number_of_updates=1)
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids = db.getDocIds(cbl_db2)

    # Update the same documents concurrently in all CBL DBs
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

    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    replicator.wait_until_replicator_idle(repl3)
    replicator.stop(repl3)
    time.sleep(2)  # give sometime to restart the replicator
    # Replicate to Sync-gateway
    while replicator.getActivitylevel(repl) != "stopped":
        log_info("replicator activity for repl: {}".format(replicator.getActivitylevel(repl)))
        time.sleep(2)

    while replicator.getActivitylevel(repl3) != "stopped":
        log_info("replicator activity for repl3: {}".format(replicator.getActivitylevel(repl3)))
        time.sleep(0.5)
    repl_config = replicator.configure(cbl_db3, sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl4 = replicator.create(repl_config)
    process_replicator(replicator, repl4)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_docs = sg_docs["rows"]
    cbl_doc_ids = db.getDocIds(cbl_db3)
    assert len(cbl_doc_ids) == len(sg_docs)
    sg_ids = [row["id"] for row in sg_docs]
    for doc in cbl_doc_ids:
        assert doc in sg_ids, "cbl db3 docs did not get replicated to sync gateway"

    if no_conflicts_enabled:
        for doc in sg_docs:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                       auth=session)
            assert str(he.value).startswith('409 Client Error: Conflict for url:')


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2),
    ('listener_tests/listener_tests_no_conflicts', 100, 5),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_multiple_cbls_updates_concurrently_with_pull(params_from_base_test_setup, setup_customized_teardown_test, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in SG.
        2. Do Pull replication to 3 CBLs
        3. update docs in SG and all 3 CBL.
        4. PUSH and PULL replication to CBLs
        5. Verify docs can resolve conflicts and
        should able to replicate docs to CBL
        6. Update docs through all 3 CBLs
        7. Verify docs can be updated
        8. Add verification of sync-gateway
    """

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
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
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # Create CBL databases
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]

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
    with ThreadPoolExecutor(max_workers=10) as tpe:
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
    log_info("repl1 error: {}".format(replicator.getError(repl1)))
    replicator.stop(repl1)
    replicator.wait_until_replicator_idle(repl2)
    log_info("repl2 error: {}".format(replicator.getError(repl2)))
    replicator.stop(repl2)
    replicator.wait_until_replicator_idle(repl3)
    log_info("repl3 error: {}".format(replicator.getError(repl3)))
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
    replicate_update_cbl_docs(replicator, db, cbl_db2, repl2)

    repl_config = replicator.configure(cbl_db3, target_url=sg_blip_url, continuous=True,
                                       channels=channels, replicator_authenticator=replicator_authenticator)
    repl3 = replicator.create(repl_config)
    # This method includes assertion for updates
    replicate_update_cbl_docs(replicator, db, cbl_db3, repl3)


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates, add_attachments", [
    ('listener_tests/listener_tests_no_conflicts', 10, 2, False),
    ('listener_tests/listener_tests_no_conflicts', 10, 10, True),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10, True)
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
        8. Add verification of sync-gateway
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

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

    # Replicate to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(cbl_db, target_url=sg_blip_url, replication_type="pull", continuous=True,
                                               replicator_authenticator=replicator_authenticator)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(cbl_doc_ids) == len(sg_docs)

    # Update the same documents concurrently from a sync gateway client and and CBL client
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_cbl_task1 = tpe.submit(
            db.update_bulk_docs,
            database=cbl_db,
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
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, channels=channels, replicator_authenticator=replicator_authenticator)
    repl2 = replicator.create(repl_config)
    # This method includes assertion for updates
    replicate_update_cbl_docs(replicator, db, cbl_db, repl2)


@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs, number_of_updates", [
    ('listener_tests/listener_tests_no_conflicts', 10, 4),
    ('listener_tests/listener_tests_no_conflicts', 100, 10),
    ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_CBL_push_without_pull(params_from_base_test_setup, sg_conf_name, num_of_docs, number_of_updates):
    """
        @summary:
        1. Create docs in SG.
        2. Pull replication to CBL
        3. update docs in SG .
        4. Update docs in CBL(without doing pull).
        5. Push replication.
        6. Verify conflicts not created with no-conflicts mode/ creates conflicts with no-conflicts disabled
    """

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["no-conflicts-channel"]
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    # Modify sync-gateway config to use no-conflicts config
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
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # 2. Pull replication to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="pull", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 3. Update the docs few times
    for i in range(number_of_updates):
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                              auth=session, channels=channels)

    # 4. Update docs in CBL(without pull replication from SG)
    db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates)

    # 5. Push replication to SG
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # 6 Get sg docs
    sg_conflict_resolved_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)

    sg_docs = sg_conflict_resolved_docs["rows"]
    if no_conflicts_enabled:
        for doc in sg_docs:
            with pytest.raises(HTTPError) as he:
                sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                       auth=session)
            assert str(he.value).startswith('409 Client Error: Conflict for url:')
    else:
        for doc in sg_docs:
            conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["value"]["rev"], new_revision="2-2B",
                                                    auth=session, attachment_name="sample_text.txt")
            assert conflicted_rev["rev"] == "2-2B"


def process_replicator(replicator, repl, repl_change_listener=None):

    max_times = 50
    count = 0
    replicator.start(repl)
    # Sleep until replicator completely processed
    while(replicator.getActivitylevel(repl) != "idle" and count < max_times):
        time.sleep(0.5)
        count += 1

    if repl_change_listener is not None:
        changes = replicator.getChangesChangeListener(repl_change_listener)
        log_info("changes are {}".format(changes))
    replicator.stop(repl)


def replicate_update_cbl_docs(replicator, db, cbl_db, repl):
    change_listener = replicator.addChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    # update CBL docs
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    error = replicator.getError(repl)

    for doc in cbl_db_docs:
        try:
            updates = cbl_db_docs[doc]["updates"]
        except Exception:
            updates = 0
        try:
            updates_cbl = cbl_db_docs[doc]["updates-cbl"]
        except Exception:
            updates_cbl = 0
        total_updates = updates + updates_cbl
        assert total_updates > 0, "Either CBL or sg did not update the doc right"

    replicator.wait_until_replicator_idle(repl)
    changes = replicator.getChangesChangeListener(change_listener)
    log_info(changes)
    error = replicator.getError(repl)
    replicator.stop(repl)

    return cbl_db_docs, error


def verify_sg_docs_after_replication(no_conflicts_enabled, sg_client, sg_url, sg_db, session, error):
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    for doc in sg_docs["rows"]:
        doc_body = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc["id"], auth=session)
        assert doc_body["updates-cbl"] > 0
