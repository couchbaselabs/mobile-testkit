import time
import os

import pytest

import concurrent.futures

from testkit.admin import Admin
from testkit.verify import verify_changes
from testkit.cluster import Cluster

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.Logging import Logging
from libraries.NetworkUtils import NetworkUtils


# This will be called once for the first test in the directory.
# After all the tests have completed in the directory
# the function will execute everything after the yield
@pytest.fixture(scope="module")
def setup_1sg_2ac_1cbs_suite(request):
    log_info("Setting up 'setup_1sg_2ac_1cbs_suite' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    # Set the CLUSTER_CONFIG environment variable to 1sg_2ac_1cbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("1sg_2ac_1cbs")

    cluster_helper.provision_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
    )

    yield

    cluster_helper.unset_cluster_config()

    log_info("Tearing down 'setup_1sg_2ac_1cbs_suite' ...")


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_1sg_2ac_1cbs_test(request):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    yield {"cluster_config": os.environ["CLUSTER_CONFIG"]}

    log_info("Tearing down test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_2ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_dcp_reshard_sync_gateway_goes_down(setup_1sg_2ac_1cbs_test, sg_conf):

    cluster_conf = setup_1sg_2ac_1cbs_test["cluster_config"]

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


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_2ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_dcp_reshard_sync_gateway_comes_up(setup_1sg_2ac_1cbs_test, sg_conf):

    cluster_conf = setup_1sg_2ac_1cbs_test["cluster_config"]

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

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_2ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_dcp_reshard_single_sg_accel_goes_down_and_up(setup_1sg_2ac_1cbs_test, sg_conf):

    cluster_conf = setup_1sg_2ac_1cbs_test["cluster_config"]

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

    # Verify that all sync_gateways and
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_2ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/performance/sync_gateway_default_performance.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_pindex_distribution(setup_1sg_2ac_1cbs_test, sg_conf):

    # the test itself doesn't have to do anything beyond calling cluster.reset() with the
    # right configuration, since the validation of the cbgt pindex distribution is in the
    # cluster.reset() method itself.

    cluster_conf = setup_1sg_2ac_1cbs_test["cluster_config"]

    log_info("Running 'test_pindex_distribution'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0
