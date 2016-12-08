import concurrent.futures
import os

import pytest

import keywords.constants
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.SyncGateway import validate_sync_gateway_mode
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from libraries.NetworkUtils import NetworkUtils


# This will be called once at the beggining of the execution in the 'tests/load_balancer' directory
# and will be torn down, (code after the yeild) after each .py file in this directory
@pytest.fixture(scope="module")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use load_balancer_cc cluster config if mode is "cc" or load_balancer_di cluster config if mode is "di"
    cluster_config = "{}/load_balancer_{}".format(keywords.constants.CLUSTER_CONFIGS_DIR, mode)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    # Skip provisioning if user specifies '--skip-provisoning'
    if not skip_provisioning:
        cluster_helper = ClusterKeywords()
        cluster_helper.provision_cluster(
            cluster_config=cluster_config,
            server_version=server_version,
            sync_gateway_version=sync_gateway_version,
            sync_gateway_config=sg_config
        )

    yield {"cluster_config": cluster_config, "mode": mode}

    log_info("Tearing down 'params_from_base_suite_setup' ...")


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]

    yield {
        "cluster_config": cluster_config,
        "mode": mode
    }

    log_info("Tearing down test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.nginx
@pytest.mark.changes
def test_load_balance_sanity(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_util = ClusterKeywords()
    cluster_util.reset_cluster(
        cluster_config=cluster_config,
        sync_gateway_config=sg_conf_path
    )

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
        ct_task = executor.submit(ct.start)
        log_info("Adding docs ...")
        docs = client.add_docs(lb_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        assert len(docs) == num_docs

        log_info("Adding docs done")
        wait_for_changes = executor.submit(ct.wait_until, docs)

        if wait_for_changes.result():
            log_info("Stopping ...")
            log_info("Found all docs ...")
            executor.submit(ct.stop)
            ct_task.result()
        else:
            executor.submit(ct.stop)
            ct_task.result()
            raise Exception("Could not find all changes in feed before timeout!!")
