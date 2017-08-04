import time

import pytest

import concurrent.futures

from libraries.testkit.admin import Admin
from libraries.testkit.verify import verify_changes
from libraries.testkit.cluster import Cluster

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import SYNC_GATEWAY_CONFIGS

from keywords.MobileRestClient import MobileRestClient

from keywords import userinfo
from keywords import document
from keywords import couchbaseserver
from keywords.SyncGateway import SyncGateway
from keywords import exceptions


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
])
def test_dcp_reshard_sync_gateway_goes_down(params_from_base_test_setup, sg_conf):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_sync_gateway_goes_down'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log_info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        log_info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000)] = "seth"

        log_info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 2000, bulk=True)] = "traun"

        # stop sg_accel
        shutdown_status = cluster.sg_accels[0].stop()
        assert shutdown_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log_info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(120)

    verify_changes(traun, expected_num_docs=2000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=8000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify that the sg1 is down but the other sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 1 and errors[0][0].hostname == "ac1"

    # Restart the failing node so that cluster verification does not blow up in test teardown
    start_status = cluster.sg_accels[0].start(sg_conf)
    assert start_status == 0


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
])
def test_dcp_reshard_sync_gateway_comes_up(params_from_base_test_setup, sg_conf):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_sync_gateway_goes_down'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    stop_status = cluster.sg_accels[0].stop()
    assert stop_status == 0, "Failed to stop sg_accel"

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log_info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        time.sleep(5)

        log_info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 6000)] = "traun"

        log_info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 4000)] = "seth"

        # Bring up a sync_gateway
        up_status = cluster.sg_accels[0].start(sg_conf)
        assert up_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log_info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(120)

    verify_changes(traun, expected_num_docs=6000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=4000, expected_num_revisions=0, expected_docs=seth.cache)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS),
])
def test_dcp_reshard_single_sg_accel_goes_down_and_up(params_from_base_test_setup, sg_conf):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_single_sg_accel_goes_down_and_up'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Stop the second sg_accel
    stop_status = cluster.sg_accels[1].stop()
    assert stop_status == 0, "Failed to stop sg_accel"

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log_info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        log_info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000)] = "seth"

        log_info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 10000, bulk=True)] = "traun"

        # take down a sync_gateway
        shutdown_status = cluster.sg_accels[0].stop()
        assert shutdown_status == 0

        # Add more docs while no writers are online
        log_info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 2000, bulk=True)] = "seth"

        # Start a single writer
        start_status = cluster.sg_accels[0].start(sg_conf)
        assert start_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log_info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(300)

    verify_changes(traun, expected_num_docs=10000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=10000, expected_num_revisions=0, expected_docs=seth.cache)

    # Start second writer again
    start_status = cluster.sg_accels[1].start(sg_conf)
    assert start_status == 0


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.parametrize("sg_conf", [
    ("{}/performance/sync_gateway_default_performance.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_pindex_distribution(params_from_base_test_setup, sg_conf):

    # the test itself doesn't have to do anything beyond calling cluster.reset() with the
    # right configuration, since the validation of the cbgt pindex distribution is in the
    # cluster.reset() method itself.

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_pindex_distribution'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS),
])
def test_take_down_bring_up_sg_accel_validate_cbgt(params_from_base_test_setup, sg_conf):
    """
    Scenario 1

    Start with 3 sg_accels
    Take down 2 sg_accels (block until down -- poll port if needed)
    Doc adds with uuids (~30 sec for cbgt to reshard)
    polling loop: wait for all docs to come back over changes feed
    Call validate pindex with correct number of accels

    Scenario 2 (Continuation)

    When bringing up, you'd have to poll the cbgt_cfg until you get expected number of nodes,
    then you could validate the pindex with 2 accels
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_single_sg_accel_goes_down_and_up'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_conf)

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    client = MobileRestClient()

    doc_pusher_user_info = userinfo.UserInfo("doc_pusher", "pass", channels=["A"], roles=[])
    doc_pusher_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=doc_pusher_user_info.name,
        password=doc_pusher_user_info.password,
        channels=doc_pusher_user_info.channels
    )

    log_info("Shutting down sg_accels: [{}, {}]".format(cluster.sg_accels[1], cluster.sg_accels[2]))
    # Shutdown two accel nodes in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        sg_accel_down_task_1 = ex.submit(cluster.sg_accels[1].stop)
        sg_accel_down_task_2 = ex.submit(cluster.sg_accels[2].stop)
        assert sg_accel_down_task_1.result() == 0
        assert sg_accel_down_task_2.result() == 0

    log_info("Finished taking nodes down!")

    # It should take some time ~30 for cbgt to pick up failing nodes and reshard the pindexes. During
    # this add a 1000 docs a start a longpoll changes loop to see if those docs make to to the changes feed
    # If the reshard is successful they will show up at somepoint after. If not, the docs will fail to show up.
    doc_pusher_docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=1000,
        id_prefix=None,
        auth=doc_pusher_auth,
        channels=doc_pusher_user_info.channels
    )
    assert len(doc_pusher_docs) == 1000
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=doc_pusher_docs, auth=doc_pusher_auth, polling_interval=5)

    # The pindexes should be reshared at this point since all of the changes have shown up
    assert cluster.validate_cbgt_pindex_distribution(num_running_sg_accels=1)

    log_info("Start sg_accels: [{}, {}]".format(cluster.sg_accels[1], cluster.sg_accels[2]))

    # Start two accel nodes in parallel
    status = cluster.sg_accels[1].start(sg_conf)
    assert status == 0

    # Poll on pIndex reshard after bring 2 accel nodes back
    assert cluster.validate_cbgt_pindex_distribution_retry(num_running_sg_accels=2)

    status = cluster.sg_accels[2].start(sg_conf)
    assert status == 0

    # Poll on pIndex reshard after bring 2 accel nodes back
    assert cluster.validate_cbgt_pindex_distribution_retry(num_running_sg_accels=3)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.session
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS),
])
def test_take_all_sgaccels_down(params_from_base_test_setup, sg_conf):
    """
    Scenario that takes all sync_gateway accel nodes offline during doc load.
    After bring the nodes back online during load, the reshard of the DCP feed is verified.
    The changes feed is verified that all docs show up.

    1. Start doc load (1000 doc)
    2. Take all sg_accel nodes down in parallel
    3. Verify node are down
    4. Wait for doc adds to complete, store "doc_push_result_1"
    5. Verify "doc_push_result_1" docs added
    6. Start doc load (1000 docs)
    7. Wait for 5. to complete, store "doc_push_result_2"
    8. Verify "doc_push_result_2" docs added
    9. Start another doc load (1000 docs)
    10. Bring up nodes in parallel
    11. poll on p-index reshard
    12. Wait for 9. to complete, store "doc_push_result_3"
    13. Verify "doc_push_result_3" docs added
    14. Verify "doc_push_result_1" + "doc_push_result_2" + "doc_push_result_3" show up in _changes feed
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_single_sg_accel_goes_down_and_up'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_conf)

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    num_docs = 1000

    client = MobileRestClient()

    doc_pusher_user_info = userinfo.UserInfo("doc_pusher", "pass", channels=["A"], roles=[])
    doc_pusher_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=doc_pusher_user_info.name,
        password=doc_pusher_user_info.password,
        channels=doc_pusher_user_info.channels
    )

    a_user_info = userinfo.UserInfo("a_user", "pass", channels=["A"], roles=[])
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=a_user_info.name,
        password=a_user_info.password,
        channels=a_user_info.channels
    )
    a_user_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=a_user_info.name,
        password=a_user_info.password
    )

    # Shutdown all accel nodes in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:

        # Start adding docs
        docs_1 = document.create_docs(None, num_docs, channels=doc_pusher_user_info.channels)
        docs_1_task = ex.submit(client.add_bulk_docs, url=sg_url, db=sg_db, docs=docs_1, auth=doc_pusher_auth)

        # Take down all access nodes
        log_info("Shutting down sg_accels: [{}, {}, {}] ...".format(
            cluster.sg_accels[0],
            cluster.sg_accels[1],
            cluster.sg_accels[2]
        ))
        sg_accel_down_task_1 = ex.submit(cluster.sg_accels[0].stop)
        sg_accel_down_task_2 = ex.submit(cluster.sg_accels[1].stop)
        sg_accel_down_task_3 = ex.submit(cluster.sg_accels[2].stop)
        assert sg_accel_down_task_1.result() == 0
        assert sg_accel_down_task_2.result() == 0
        assert sg_accel_down_task_3.result() == 0

        # Block until bulk_docs is complete
        doc_push_result_1 = docs_1_task.result()
        assert len(doc_push_result_1) == num_docs
        client.verify_docs_present(url=sg_url, db=sg_db, expected_docs=doc_push_result_1, auth=doc_pusher_auth)

        # Load sync_gateway with another batch of docs while the sg_accel nodes are offline
        docs_2_bodies = document.create_docs(None, num_docs, channels=doc_pusher_user_info.channels)
        docs_push_result_2 = client.add_bulk_docs(url=sg_url, db=sg_db, docs=docs_2_bodies, auth=doc_pusher_auth)
        assert len(docs_push_result_2) == num_docs
        client.verify_docs_present(url=sg_url, db=sg_db, expected_docs=docs_push_result_2, auth=doc_pusher_auth)

        # Start loading Sync Gateway with another set of docs while bringing the sg_accel nodes online
        docs_3 = document.create_docs(None, num_docs, channels=doc_pusher_user_info.channels)
        docs_3_task = ex.submit(client.add_bulk_docs, url=sg_url, db=sg_db, docs=docs_3, auth=doc_pusher_auth)

        # Bring all the sg_accel nodes back up
        # Take down all access nodes
        log_info("Starting sg_accels: [{}, {}, {}] ...".format(
            cluster.sg_accels[0],
            cluster.sg_accels[1],
            cluster.sg_accels[2]
        ))
        sg_accel_up_task_1 = ex.submit(cluster.sg_accels[0].start, sg_conf)
        sg_accel_up_task_2 = ex.submit(cluster.sg_accels[1].start, sg_conf)
        sg_accel_up_task_3 = ex.submit(cluster.sg_accels[2].start, sg_conf)
        assert sg_accel_up_task_1.result() == 0
        assert sg_accel_up_task_2.result() == 0
        assert sg_accel_up_task_3.result() == 0

        # Wait for pindex to reshard correctly
        assert cluster.validate_cbgt_pindex_distribution_retry(3)

        # Block until second bulk_docs is complete
        doc_push_result_3 = docs_3_task.result()
        assert len(doc_push_result_3) == num_docs
        client.verify_docs_present(url=sg_url, db=sg_db, expected_docs=doc_push_result_3, auth=doc_pusher_auth)

    # Combine the 3 push results and make sure the changes propagate to a_user
    # a_user has access to the doc's channel.
    log_info("Verifying all the changes show up for 'a_user' ...")
    all_docs = doc_push_result_1 + docs_push_result_2 + doc_push_result_3
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=all_docs, auth=a_user_session, polling_interval=2)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.parametrize("sg_conf", [
    ("{}/missing_num_shards_di.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_missing_num_shards(params_from_base_test_setup, sg_conf):
    """
    1. Launch sg_accels missing the following property in the config.
        "num_shards":16
    2. Verify there are 16 shards
    3. Verify they are distributed evenly across the nodes
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_missing_num_shards'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # CBGT REST Admin API endpoint
    admin_api = Admin(cluster.sg_accels[1])
    cbgt_cfg = admin_api.get_cbgt_config()

    # Verify that default number of pindex shards is 16.
    # This may change in the future in which case this test will need to be updated.
    assert cbgt_cfg.num_shards == 16

    # Verify sharding is correct
    assert cluster.validate_cbgt_pindex_distribution_retry(num_running_sg_accels=3)


# Test is invalid due to https://github.com/couchbase/sync_gateway/commit/027407219f9489a755323f58c1395623d53f4103.
# When the test was written, sync gateway should fail to start in this scenario. This behavior was removed in the
# above commit and now sync gateway will start when in this state
@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sgaccel
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.skip(reason="https://github.com/couchbase/sync_gateway/commit/027407219f9489a755323f58c1395623d53f4103")
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS),
])
def test_detect_stale_channel_index(params_from_base_test_setup, sg_conf):
    """
    1. Bring up single Sync Gateway node, backed by Couchbase Server with 3 accels indexing
    2. Configure such that the primary bucket and the channel index bucket are different (which is the norm)
    3. Add 1000 documents
    4. Shutdown Sync Gateway
    5. Delete / create the primary bucket ('data-bucket'), but do not touch the channel index bucket
    6. Start Sync Gateway
    7. Assert that sync_gateway fails to start due to stale channel index
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_detect_stale_channel_index'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_conf)

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    cb_server_url = topology["couchbase_servers"][0]
    sg_db = "db"
    num_docs = 1000

    cb_server = couchbaseserver.CouchbaseServer(url=cb_server_url)
    client = MobileRestClient()

    # Create doc pusher user
    doc_pusher_user_info = userinfo.UserInfo(name="doc_pusher", password="pass", channels=["NASA"], roles=[])
    doc_pusher_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=doc_pusher_user_info.name,
        password=doc_pusher_user_info.password,
        channels=doc_pusher_user_info.channels
    )

    # Add some docs to Sync Gateway to cause indexing
    docs = document.create_docs(None, number=num_docs, channels=doc_pusher_user_info.channels)
    pushed_docs = client.add_bulk_docs(url=sg_url, db=sg_db, docs=docs, auth=doc_pusher_auth)
    assert len(pushed_docs) == num_docs

    # Shut down sync_gateway
    sg_util = SyncGateway()
    sg_util.stop_sync_gateways(cluster_config=cluster_conf, url=sg_url)

    # Delete server bucket
    cb_server.delete_bucket(name="data-bucket")

    # Create server bucket
    ram_per_bucket_mb = cb_server.get_ram_per_bucket(num_buckets=2)
    cb_server.create_bucket(name="data-bucket", ram_quota_mb=ram_per_bucket_mb)

    # Start sync_gateway and assert that a Provisioning error is raised due to detecting stale index
    with pytest.raises(exceptions.ProvisioningError):
        sg_util.start_sync_gateways(cluster_config=cluster_conf, url=sg_url, config=sg_conf)

    # TODO: To make this check even more accurate, could
    # run remote ssh command "systemctl status sync_gateway.service" and look for
    # regex pattern: Main PID: 7185 (code=exited, status=2)

    # Delete index bucket and recreate it
    cb_server.delete_bucket(name="index-bucket")
    cb_server.create_bucket(name="index-bucket", ram_quota_mb=ram_per_bucket_mb)

    # Start sync gateway, should succeed now
    sg_util.start_sync_gateways(cluster_config=cluster_conf, url=sg_url, config=sg_conf)
