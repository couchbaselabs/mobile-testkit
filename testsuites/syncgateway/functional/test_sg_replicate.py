from testkit.cluster import Cluster
from testkit.admin import Admin
from testkit.syncgateway import wait_until_doc_sync
from testkit.syncgateway import wait_until_active_tasks_empty
from testkit.syncgateway import wait_until_active_tasks_non_empty
from testkit.syncgateway import wait_until_doc_in_changes_feed
from testkit.syncgateway import wait_until_docs_sync
from testkit.syncgateway import assert_does_not_have_doc
from testkit.syncgateway import assert_has_doc
from requests import HTTPError

import time

DB1 = "db1"
DB2 = "db2"
DEFAULT_CONFIG_PATH = "resources/sync_gateway_configs/sync_gateway_sg_replicate_cc.json"


def test_sg_replicate_basic_test():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    # Add docs to sg1 and sg2
    doc_id_sg1 = sg1_user.add_doc()
    doc_id_sg2 = sg2_user.add_doc()

    # Wait until docs show up in changes feed
    wait_until_doc_in_changes_feed(sg1, DB1, doc_id_sg1)
    wait_until_doc_in_changes_feed(sg2, DB2, doc_id_sg2)

    # Make sure it doesn't appear on the target DB
    # even without starting a replication (which will
    # happen if the SG's are sharing a CB bucket)
    time.sleep(5)
    assert_does_not_have_doc(sg2_user, doc_id_sg1)
    assert_does_not_have_doc(sg1_user, doc_id_sg2)

    # Start a push replication sg1 -> sg2
    replication_result = sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=False,
        use_remote_source=True,
        use_admin_url=True
    )

    assert replication_result["continuous"] is False
    assert replication_result["docs_written"] == 2
    assert replication_result["docs_read"] == 2
    assert replication_result["doc_write_failures"] == 0

    # Start a pull replication sg1 <- sg2
    replication_result = sg1.start_pull_replication(
        sg2.admin.admin_url,
        DB2,
        DB1,
        continuous=False,
        use_remote_target=True,
        use_admin_url=True
    )

    assert replication_result["continuous"] is False
    assert replication_result["docs_written"] == 2
    assert replication_result["docs_read"] == 2
    assert replication_result["doc_write_failures"] == 0

    # Verify that the doc added to sg1 made it to sg2
    assert_has_doc(sg2_user, doc_id_sg1)

    # Verify that the doc added to sg2 made it to sg1
    assert_has_doc(sg1_user, doc_id_sg2)


def test_sg_replicate_basic_test_channels():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1a_user, sg1b_user, sg2_user = create_sg_users_channels(sg1, sg2, DB1, DB2)

    # Add docs to sg1 in channel A and channel B
    doc_id_sg1a = sg1a_user.add_doc()
    doc_id_sg1b = sg1b_user.add_doc()

    # Wait until docs show up in changes feed
    wait_until_doc_in_changes_feed(sg1, DB1, doc_id_sg1a)
    wait_until_doc_in_changes_feed(sg1, DB1, doc_id_sg1b)

    # Make sure it doesn't appear on the target DB
    # even without starting a replication (which will
    # happen if the SG's are sharing a CB bucket)
    time.sleep(5)
    assert_does_not_have_doc(sg2_user, doc_id_sg1a)
    assert_does_not_have_doc(sg2_user, doc_id_sg1b)

    # Start a push replication sg1 -> sg2
    chans = sg1a_user.channels
    sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=False,
        use_remote_source=True,
        channels=chans,
        use_admin_url=True
    )

    # Verify that the doc added to sg1 made it to sg2
    assert_has_doc(sg2_user, doc_id_sg1a)


def test_sg_replicate_continuous_replication():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    # Create users (in order to add docs)
    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    # Kick off continuous replication
    sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=True,
        use_remote_source=True,
        use_admin_url=True
    )

    # Add docs
    doc_id = sg1_user.add_doc()

    # Wait til all docs sync to target
    wait_until_docs_sync(sg2_user, [doc_id])

    # Shutdown target
    sg2.stop()

    # Add more docs
    doc_id_2 = sg1_user.add_doc()

    # Wait a few seconds to give the source replicator time to have some attempts
    time.sleep(5)

    # Restart target
    sg2.start(config=DEFAULT_CONFIG_PATH)

    # Wait til all docs sync to target
    wait_until_docs_sync(sg2_user, [doc_id, doc_id_2])

    # Stop replications
    sg1.stop_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=True,
        use_remote_source=True,
        use_admin_url=True
    )

    # Wait until active_tasks is empty (or throw exception)
    wait_until_active_tasks_empty(sg1)

    # Add more docs, even though the replication is already stopped
    doc_id_3 = sg1_user.add_doc()

    # Wait a few seconds to give it time to potentially propagate
    time.sleep(5)

    # Make sure the doc did not propagate to the target
    assert_does_not_have_doc(sg2_user, doc_id_3)


def test_sg_replicate_delete_db_replication_in_progress():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    # Kick off continuous replication
    sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=True,
        use_remote_source=True,
        use_admin_url=True
    )

    # Wait until active_tasks is non empty
    wait_until_active_tasks_non_empty(sg1)

    # Delete the database
    sg1.admin.delete_db(DB1)
    sg2.admin.delete_db(DB2)

    # Query active tasks and make sure the replication is gone
    wait_until_active_tasks_empty(sg1)


def test_sg_replicate_non_existent_db():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    # Start a push replication
    got_exception = False
    try:
        sg1.start_push_replication(
            sg2.admin.admin_url,
            DB1,
            DB2,
            continuous=False,
            use_remote_source=True,
            use_admin_url=True
        )
    except HTTPError:
        got_exception = True

    assert got_exception is True


def test_sg_replicate_push_async(num_docs):

    assert num_docs > 0

    # if the async stuff works, we should be able to kick off a large
    # push replication and get a missing doc before the replication has
    # a chance to finish.  And then we should later see that doc.

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    # Add docs to sg1
    doc_ids_added = []
    last_doc_id_added = None
    for i in xrange(num_docs):
        doc_id = sg1_user.add_doc()
        doc_ids_added.append(doc_id)
        last_doc_id_added = doc_id

    # Wait until doc shows up on sg1's changes feed
    wait_until_doc_in_changes_feed(sg1, DB1, last_doc_id_added)

    # try to get the last doc added from the target -- assert that we get an exception
    assert_does_not_have_doc(sg2_user, last_doc_id_added)

    # kick off a one-off push replication with async=true
    sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=False,
        use_remote_source=True,
        async=True,
        use_admin_url=True
    )

    # wait until that doc shows up on the target
    wait_until_doc_sync(sg2_user, last_doc_id_added)

    # At this point, the active tasks should be empty
    wait_until_active_tasks_empty(sg1)


def test_stop_replication_via_replication_id():

    sg1, sg2 = create_sync_gateways(DEFAULT_CONFIG_PATH)

    # Create users (in order to add docs)
    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    # Kick off continuous replication
    sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=True,
        use_remote_source=True,
        use_admin_url=True
    )

    # Make sure there is one active task
    active_tasks = sg1.admin.get_active_tasks()
    assert len(active_tasks) == 1
    active_task = active_tasks[0]

    # get the replication id from the active tasks
    replication_id = active_task["replication_id"]

    # stop the replication
    sg1.stop_replication_by_id(replication_id, use_admin_url=True)

    # verify that the replication is stopped
    active_tasks = sg1.admin.get_active_tasks()
    print "active_tasks after stop: {}".format(active_tasks)
    assert len(active_tasks) == 0


def test_replication_config():

    sg1, sg2 = create_sync_gateways("resources/sync_gateway_configs/sync_gateway_sg_replicate_continuous_cc.json")

    # Wait until active_tasks is non empty
    wait_until_active_tasks_non_empty(sg1)

    pass


def create_sync_gateways(config_path):

    cluster = Cluster()
    cluster.reset(config_path=config_path)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]

    return sg1, sg2


def create_sg_users_channels(sg1, sg2, db1, db2):
    admin1 = Admin(sg1)
    admin2 = Admin(sg2)
    sg1a_user = admin1.register_user(
        target=sg1,
        db=db1,
        name="sg1A_user",
        password="sg1A_user",
        channels=["A"],
    )
    sg1b_user = admin1.register_user(
        target=sg1,
        db=db1,
        name="sg1B_user",
        password="sg1B_user",
        channels=["B"],
    )
    sg2_user = admin2.register_user(
        target=sg2,
        db=db2,
        name="sg2_user",
        password="sg2_user",
        channels=["*"],
    )

    return sg1a_user, sg1b_user, sg2_user


def create_sg_users(sg1, sg2, db1, db2):

    admin1 = Admin(sg1)
    admin2 = Admin(sg2)
    sg1_user = admin1.register_user(
        target=sg1,
        db=db1,
        name="sg1_user",
        password="sg1_user",
        channels=["A"],
    )
    sg2_user = admin2.register_user(
        target=sg2,
        db=db2,
        name="sg2_user",
        password="sg2_user",
        channels=["A"],
    )
    return sg1_user, sg2_user
