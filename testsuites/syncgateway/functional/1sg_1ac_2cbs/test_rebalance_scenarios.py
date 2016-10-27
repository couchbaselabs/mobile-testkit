import os
import time
import uuid

import pytest
import concurrent.futures

from libraries.testkit.cluster import Cluster
from libraries.NetworkUtils import NetworkUtils

from keywords.exceptions import TimeoutError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.MobileRestClient import MobileRestClient
from keywords.CouchbaseServer import CouchbaseServer


# This will be called once for the first test in the file.
# After all the tests have completed the function will execute everything after the yield
@pytest.fixture(scope="module")
def setup_1sg_1ac_2cbs_suite(request):
    log_info("Setting up 'setup_1sg_1ac_2cbs_suite' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    skip_provisioning = request.config.getoption("--skip-provision")

    # Set the CLUSTER_CONFIG environment variable to 1sg_1ac_1cbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("1sg_1ac_2cbs")

    if not skip_provisioning:
        cluster_helper.provision_cluster(
            cluster_config=os.environ["CLUSTER_CONFIG"],
            server_version=server_version,
            sync_gateway_version=sync_gateway_version,
            sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
        )

    yield

    log_info("Tearing down 'setup_1sg_1ac_2cbs_suite' ...")
    cluster_helper.unset_cluster_config()


# This is called before each test and will yield the cluster config to each test in the file
# After each test, the function will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_1sg_1ac_2cbs_test(request):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    # Reset cluster
    cluster_helper = ClusterKeywords()
    cluster_helper.reset_cluster(cluster_config=os.environ["CLUSTER_CONFIG"],
                                 sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS))

    cluster_config = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    yield cluster_config

    log_info("Tearing down test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.rebalance
@pytest.mark.usefixtures("setup_1sg_1ac_2cbs_suite")
def test_distributed_index_rebalance_sanity(setup_1sg_1ac_2cbs_test):

    cluster_config = setup_1sg_1ac_2cbs_test

    log_info(cluster_config)

    admin_sg_one = cluster_config["sync_gateways"][0]["admin"]
    sg_one_url = cluster_config["sync_gateways"][0]["public"]
    cbs_one_url = cluster_config["couchbase_servers"][0]
    cbs_two_url = cluster_config["couchbase_servers"][1]

    sg_db = "db"
    num_docs = 100
    num_updates = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    cb_server = CouchbaseServer(cbs_one_url)

    client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    with concurrent.futures.ThreadPoolExecutor(5) as executor:

        # Add docs to sg
        log_info("Adding docs to sync_gateway")
        docs, errors = client.add_docs(sg_one_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        assert len(docs) == num_docs
        assert len(errors) == 0

        # Start updating docs and rebalance out one CBS node
        log_info("Updating docs on sync_gateway")
        update_docs_task = executor.submit(client.update_docs, sg_one_url, sg_db, docs, num_updates, auth=session)

        rebalance_task = executor.submit(cb_server.rebalance_out, server_to_remove=cbs_two_url)
        assert rebalance_task.result(), "Rebalance out unsuccessful for {}!".format(cbs_two_url)

        updated_docs = update_docs_task.result()
        log_info(updated_docs)

    # Verify docs / revisions present
    client.verify_docs_present(sg_one_url, sg_db, updated_docs, auth=session)

    # Verify docs revisions in changes feed
    client.verify_docs_in_changes(sg_one_url, sg_db, updated_docs, auth=session)

    # Rebalance Server back in to the pool
    assert cb_server.rebalance_in(server_to_add=cbs_two_url), "Could not rebalance node back in .."

    # Verify all sgs and accels are still running
    cluster = Cluster()
    errors = cluster.verify_alive("distributed_index")
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.rebalance
@pytest.mark.usefixtures("setup_1sg_1ac_2cbs_suite")
def test_server_goes_down_sanity(setup_1sg_1ac_2cbs_test):
    """
    1. Start with a two node couchbase server cluster
    2. Starting adding docs
    3. Kill one of the server nodes and signal completion
    4. Stop adding docs
    5. Verify that that the expected docs are present and in the changes feed.
    6. Start server again and add to cluster
    """

    cluster_config = setup_1sg_1ac_2cbs_test

    log_info(cluster_config)

    admin_sg = cluster_config["sync_gateways"][0]["admin"]
    sg_url = cluster_config["sync_gateways"][0]["public"]
    cbs_two_url = cluster_config["couchbase_servers"][1]

    sg_db = "db"
    num_docs = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    cb_server = CouchbaseServer(cbs_two_url)

    client.create_user(admin_sg, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg, sg_db, sg_user_name)

    # Stop second server
    cb_server.stop()

    # Try to add 100 docs in a loop until all succeed, if the never do, fail with timeout
    errors = num_docs
    timeout = 15
    start = time.time()

    while errors != 0:
        # Fail tests if all docs do not succeed before timeout
        if (time.time() - start) > timeout:
            # Bring server back up before failing the test
            cb_server.start()
            raise TimeoutError("Failed to successfully put docs before timeout")

        docs, errors = client.add_docs(url=sg_url, db=sg_db, number=num_docs, id_prefix=str(uuid.uuid4()), auth=session, allow_errors=True)
        errors = len(errors)
        log_info("Seeing: {} errors".format(errors))

        time.sleep(1)

    # TODO: Verify GET (bulk) of docs
    # TODO: Verify _changes (basic) feed

    # Test succeeded without timeout, bring server back into topology
    cb_server.start()

    # Make sure all docs were not added before server was
    log_info("test_server_goes_down_sanity complete!")
