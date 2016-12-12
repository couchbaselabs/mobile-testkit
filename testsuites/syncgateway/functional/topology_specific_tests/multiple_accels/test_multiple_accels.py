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


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
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


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
])
def test_dcp_reshard_sync_gateway_comes_up(params_from_base_test_setup, sg_conf):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_sync_gateway_goes_down'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

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
    time.sleep(60)

    verify_changes(traun, expected_num_docs=6000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=4000, expected_num_revisions=0, expected_docs=seth.cache)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf", [
    "{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS),
])
def test_dcp_reshard_single_sg_accel_goes_down_and_up(params_from_base_test_setup, sg_conf):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    log_info("Running 'test_dcp_reshard_single_sg_accel_goes_down_and_up'")
    log_info("cluster_conf: {}".format(cluster_conf))

    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

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
    time.sleep(120)

    verify_changes(traun, expected_num_docs=10000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=10000, expected_num_revisions=0, expected_docs=seth.cache)

    # Start second writer again
    start_status = cluster.sg_accels[1].start(sg_conf)
    assert start_status == 0


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
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
