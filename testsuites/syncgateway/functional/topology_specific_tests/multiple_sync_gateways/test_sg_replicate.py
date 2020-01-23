
from libraries.testkit.cluster import Cluster
from libraries.testkit.admin import Admin
from libraries.testkit.syncgateway import wait_until_doc_sync
from libraries.testkit.syncgateway import wait_until_active_tasks_empty
from libraries.testkit.syncgateway import wait_until_active_tasks_non_empty
from libraries.testkit.syncgateway import wait_until_doc_in_changes_feed
from libraries.testkit.syncgateway import wait_until_docs_sync
from libraries.testkit.syncgateway import assert_does_not_have_doc
from libraries.testkit.syncgateway import assert_has_doc
from keywords.ClusterKeywords import ClusterKeywords
from requests import HTTPError
from keywords import document
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient

import pytest

import time
import logging

from keywords.utils import log_info
from keywords.SyncGateway import sync_gateway_config_path_for_mode, create_sync_gateways

DB1 = "db1"
DB2 = "db2"


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.channel
@pytest.mark.basicauth
@pytest.mark.changes
def test_sg_replicate_basic_test(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    log_info("Running 'test_sg_replicate_basic_test'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    if sync_gateway_version >= "2.5.0":
        sg_client = MobileRestClient()
        expvars = sg_client.get_expvars(sg2.admin.admin_url)
        process_memory_resident = expvars["syncgateway"]["global"]["resource_utilization"]["process_memory_resident"]
        system_memory_total = expvars["syncgateway"]["global"]["resource_utilization"]["system_memory_total"]
        goroutines_high_watermark = expvars["syncgateway"]["global"]["resource_utilization"]["goroutines_high_watermark"]
        chan_cache_hits = expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_hits"]
        chan_cache_active_revs = expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_active_revs"]
        chan_cache_num_channels = expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_num_channels"]
        chan_cache_max_entries = expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_max_entries"]

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
    # Should block until replication
    # Result should contain the stats of the completed replication
    replication_result = sg1.start_push_replication(
        sg2.admin.admin_url,
        DB1,
        DB2,
        continuous=False,
        use_remote_source=True,
        use_admin_url=True
    )

    logging.debug("replication_result 1: {}".format(replication_result))

    assert replication_result["continuous"] is False, 'replication_result["continuous"] != False'
    assert replication_result["docs_written"] == 1, 'replication_result["docs_written"] != 1'
    assert replication_result["docs_read"] == 1, 'replication_result["docs_read"] != 1'
    assert replication_result["doc_write_failures"] == 0, 'replication_result["doc_write_failures"] != 0'

    # Start a pull replication sg1 <- sg2
    replication_result = sg1.start_pull_replication(
        sg2.admin.admin_url,
        DB2,
        DB1,
        continuous=False,
        use_remote_target=True,
        use_admin_url=True
    )

    logging.debug("replication_result 2: {}".format(replication_result))

    assert replication_result["continuous"] is False, 'replication_result["continuous"] != False'
    assert replication_result["docs_written"] == 1, 'replication_result["docs_written"] != 1'
    assert replication_result["docs_read"] == 1, 'replication_result["docs_read"] != 1'
    assert replication_result["doc_write_failures"] == 0, 'replication_result["doc_write_failures"] != 0'

    # Verify that the doc added to sg1 made it to sg2
    assert_has_doc(sg2_user, doc_id_sg1)

    # Verify that the doc added to sg2 made it to sg1
    assert_has_doc(sg1_user, doc_id_sg2)

    time.sleep(240)
    if sync_gateway_version >= "2.5.0":
        expvars = sg_client.get_expvars(sg2.admin.admin_url)
        assert process_memory_resident < expvars["syncgateway"]["global"]["resource_utilization"]["process_memory_resident"], "process_memory_resident did not get incremented"
        assert expvars["syncgateway"]["global"]["resource_utilization"]["process_cpu_percent_utilization"] > 0, "process_cpu_percent_utilization did not get incremented"
        assert system_memory_total < expvars["syncgateway"]["global"]["resource_utilization"]["system_memory_total"], "system_memory_total did not get incremented"
        assert goroutines_high_watermark < expvars["syncgateway"]["global"]["resource_utilization"]["goroutines_high_watermark"], "goroutines_high_watermark did not get incremented"
        assert chan_cache_hits < expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_hits"], "chan_cache_hits did not get incremented"
        assert chan_cache_active_revs < expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_active_revs"], "chan_cache_active_revs did not get incremented"
        assert chan_cache_num_channels < expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_num_channels"], "chan_cache_num_channels did not get incremented"
        assert chan_cache_max_entries < expvars["syncgateway"]["per_db"][DB2]["cache"]["chan_cache_max_entries"], "chan_cache_max_entries did not get incremented"
        assert expvars["syncgateway"]["per_db"][DB2]["cbl_replication_push"]["write_processing_time"] > 0, "write_processing_time did not get incremented"


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.channel
@pytest.mark.basicauth
@pytest.mark.changes
def test_sg_replicate_basic_test_channels(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_sg_replicate_basic_test_channels'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.channel
@pytest.mark.basicauth
def test_sg_replicate_continuous_replication(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_sg_replicate_continuous_replication'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg2.start(config=config)

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


# @pytest.mark.sanity
# @pytest.mark.syncgateway
# @pytest.mark.sgreplicate
# @pytest.mark.usefixtures("setup_2sg_1cbs_suite")
# def test_sg_replicate_delete_db_replication_in_progress(setup_2sg_1cbs_test):
#
#     cluster_config = setup_2sg_1cbs_test["cluster_config"]
#     log_info("Running 'test_sg_replicate_delete_db_replication_in_progress'")
#     log_info("Using cluster_config: {}".format(cluster_config))
#
#     sg1, sg2 = create_sync_gateways(
#         cluster_config=cluster_config,
#         sg_config_path=DEFAULT_CONFIG_PATH
#     )
#
#     # Kick off continuous replication
#     sg1.start_push_replication(
#         sg2.admin.admin_url,
#         DB1,
#         DB2,
#         continuous=True,
#         use_remote_source=True,
#         use_admin_url=True
#     )
#
#     # Wait until active_tasks is non empty
#     wait_until_active_tasks_non_empty(sg1)
#
#     # Delete the database
#     sg1.admin.delete_db(DB1)
#     sg2.admin.delete_db(DB2)
#
#     # Query active tasks and make sure the replication is gone
#     wait_until_active_tasks_empty(sg1)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_non_existent_db(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_sg_replicate_non_existent_db'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

    # delete databases if they exist
    try:
        sg1.admin.delete_db(DB1)
        sg2.admin.delete_db(DB2)
    except HTTPError:
        logging.debug("Got HTTPError trying to delete a DB, which means it didn't already exist")

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

    assert got_exception is True, 'Expected an exception trying to create a replication against non-existent db'


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.channel
@pytest.mark.basicauth
@pytest.mark.changes
@pytest.mark.parametrize("num_docs", [
    100,
    250
])
def test_sg_replicate_push_async(params_from_base_test_setup, num_docs):

    # if the async stuff works, we should be able to kick off a large
    # push replication and get a missing doc before the replication has
    # a chance to finish.  And then we should later see that doc.

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_sg_replicate_push_async'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)

    # Add docs to sg1
    doc_ids_added = []
    last_doc_id_added = None
    for i in range(num_docs):
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


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.channel
@pytest.mark.basicauth
def test_stop_replication_via_replication_id(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_stop_replication_via_replication_id'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    log_info("active_tasks after stop: {}".format(active_tasks))
    assert len(active_tasks) == 0


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_replication_config(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    log_info("Running 'test_replication_config'")
    log_info("Using cluster_config: {}".format(cluster_config))

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate_continuous", mode)
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

    # Wait until active_tasks is non empty
    wait_until_active_tasks_non_empty(sg1)

    pass


@pytest.mark.topospecific
@pytest.mark.syncgateway
def test_sdk_update_with_changes_request(params_from_base_test_setup):

    """
      @summary
      1.Run two Sync Gateway nodes
      2.Both with enable_shared_bucket_access
      3.Node A with import_docs:continuous
      4.Write a document to the bucket via SDK
      5.Read document via SG from node A to get rev-id for revision 1
      6.Update the document via SDK
      7.Read the update of the document from node A
      8.Request revision 1 of the document from node B

    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    channel = ['ABC']
    bucket_name = 'data-bucket-1'
    cluster_utils = ClusterKeywords(cluster_config)
    cluster = Cluster(config=cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_client = MobileRestClient()

    log_info("Running 'test_sdk_update_with_changes_request'")
    log_info("Using cluster_config: {}".format(cluster_config))
    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)
    cluster = Cluster(config=cluster_config)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]

    cluster.reset(sg_config_path=config)
    status = sg1.restart(config=config, cluster_config=cluster_config)
    assert status == 0, "Syncgateway1 did not start "
    config = sync_gateway_config_path_for_mode("sync_gateways_one_with_import_docs", mode)
    status = sg2.restart(config=config, cluster_config=cluster_config)
    assert status == 0, "Syncgateway2 did not start "
    admin1 = Admin(sg1)
    admin2 = Admin(sg2)
    # admin.admin_url = sg1.url

    sg1_user, sg2_user = create_sg_users(sg1, sg2, DB1, DB2)
    # 4.Write a document to the bucket via SDK
    log_info('Connecting to bucket ...')
    cbs_ip = host_for_url(cbs_url)
    if cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_ip, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    sdk_doc_body = document.create_docs(doc_id_prefix='sdk_doc', number=1, content={'foo': 'bar'},
                                        channels=channel)
    sdk_doc = {doc['_id']: doc for doc in sdk_doc_body}
    sdk_doc_id_list = [doc for doc in sdk_doc]
    sdk_doc_id = sdk_doc_id_list[0]
    sdk_client.upsert_multi(sdk_doc)

    # 5.Read document via SG from node A to get rev-id for revision 1
    doc = sg_client.get_doc(url=admin1.admin_url, db=DB1, doc_id=sdk_doc_id)
    print("doc is ", doc)
    revid_1 = doc["_rev"]

    # 6.Update the document via SDK
    sdk_tracking_prop = 'sdk_one_updates'
    update_docs_via_sdk(client=sdk_client, docs_to_update=sdk_doc_id_list, prop_to_update=sdk_tracking_prop, number_updates=1)

    # 7.Read the update of the document from node A
    doc = sg_client.get_doc(url=admin1.admin_url, db=DB1, doc_id=sdk_doc_id)

    # 8.Request revision 1 of the document from node B
    doc = sg_client.get_doc(url=admin2.admin_url, db=DB1, doc_id=sdk_doc_id, rev=revid_1)
    assert doc["_rev"] == revid_1, "Failed to get the doc of right revision"


def update_docs_via_sdk(client, docs_to_update, prop_to_update, number_updates):
    """ This will update a set of docs (docs_to_update)
    by updating a property (prop_to_update) using CAS safe writes.
    It will update all the docs for n times where n is number_updates.
    """

    log_info("Client: {}".format(id(client)))
    num_of_docs = len(docs_to_update)
    print("docs to update is ", docs_to_update)
    for i in range(num_of_docs):

        doc_value_result = client.get(docs_to_update[i])
        doc = doc_value_result.value
        print("doc is ", doc)
        doc_id = docs_to_update[i]
        for i in range(number_updates):
            try:
                doc[prop_to_update]
            except KeyError:
                doc[prop_to_update] = 0
            if doc[prop_to_update] is None:
                doc[prop_to_update] = 0

            doc[prop_to_update] += 1
            cur_cas = doc_value_result.cas
            client.upsert(doc_id, doc, cas=cur_cas)


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
