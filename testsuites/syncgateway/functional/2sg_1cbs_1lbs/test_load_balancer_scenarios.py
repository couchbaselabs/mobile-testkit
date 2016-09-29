import concurrent.futures
import os

import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.constants import SYNC_GATEWAY_CONFIGS

from libraries.NetworkUtils import NetworkUtils


# This will be called once for the first test in this file.
# After all the tests have completed in the directory
# the function will execute everything after the yield
@pytest.fixture(scope="module")
def setup_2sg_1cbs_1lbs_suite(request):
    log_info("Setting up 'setup_2sg_1cbs_1lbs_suite' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    # Set the CLUSTER_CONFIG environment variable to 2sg_1cbs_1lbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("2sg_1cbs_1lbs")

    cluster_helper.provision_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
    )

    yield

    cluster_helper.unset_cluster_config()

    log_info("Tearing down 'setup_2sg_1cbs_1lbs_suite' ...")


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_2sg_1cb_1lbs_test(request):

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
@pytest.mark.nginx
@pytest.mark.changes
@pytest.mark.usefixtures("setup_2sg_1cbs_1lbs_suite")
def test_load_balance_sanity(setup_2sg_1cb_1lbs_test):

    cluster_util = ClusterKeywords()

    cluster_config = setup_2sg_1cb_1lbs_test["cluster_config"]
    topology = cluster_util.get_cluster_topology(cluster_config)

    admin_sg_one = topology["sync_gateways"][0]["admin"]
    lb_url = topology["load_balancers"][0]

    sg_db = "db"
    num_docs = 1000
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()

    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    log_info(user)
    log_info(session)

    log_info("Adding docs to the load balancer ...")

    ct = ChangesTracker(url=lb_url, db=sg_db, auth=session)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        log_info("Starting ...")
        executor.submit(ct.start)
        log_info("Adding docs ...")
        add_docs_task = executor.submit(client.add_docs, lb_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)

        docs = add_docs_task.result()

        log_info("Adding docs done")
        wait_for_changes = executor.submit(ct.wait_until, docs)

        if wait_for_changes.result():
            log_info("Stopping ...")
            log_info("Found all docs ...")
            executor.submit(ct.stop)
        else:
            executor.submit(ct.stop)
            raise Exception("Could not find all changes in feed before timeout!!")
