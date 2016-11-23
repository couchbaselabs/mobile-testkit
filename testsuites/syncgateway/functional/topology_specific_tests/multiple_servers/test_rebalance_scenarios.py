import os
import time
import uuid

import pytest
import concurrent.futures

from libraries.testkit.cluster import Cluster

from keywords.exceptions import TimeoutError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.CouchbaseServer import CouchbaseServer
from keywords.SyncGateway import sync_gateway_config_path_for_mode


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.rebalance
def test_distributed_index_rebalance_sanity(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    cluster_helper = ClusterKeywords()

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper.reset_cluster(cluster_config=cluster_config,
                                 sync_gateway_config=sg_conf_path)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    admin_sg_one = topology["sync_gateways"][0]["admin"]
    sg_one_url = topology["sync_gateways"][0]["public"]
    cbs_one_url = topology["couchbase_servers"][0]
    cbs_two_url = topology["couchbase_servers"][1]

    log_info("Running: 'test_distributed_index_rebalance_sanity'")
    log_info("cluster_config: {}".format(cluster_config))
    log_info("admin_sg: {}".format(admin_sg_one))
    log_info("sg_url: {}".format(sg_one_url))
    log_info("cbs_one_url: {}".format(cbs_one_url))
    log_info("cbs_two_url: {}".format(cbs_two_url))

    sg_db = "db"
    num_docs = 100
    num_updates = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    cb_server = CouchbaseServer(cbs_one_url)
    server_to_remove = CouchbaseServer(cbs_one_url)

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

        # Run rebalance in background
        rebalance_task = executor.submit(cb_server.rebalance_out, server_to_remove)
        assert rebalance_task.result(), "Rebalance out unsuccessful for {}!".format(cbs_two_url)

        updated_docs = update_docs_task.result()
        log_info(updated_docs)

    # Verify docs / revisions present
    client.verify_docs_present(sg_one_url, sg_db, updated_docs, auth=session)

    # Verify docs revisions in changes feed
    client.verify_docs_in_changes(sg_one_url, sg_db, updated_docs, auth=session)

    # Rebalance Server back in to the pool
    cb_server.rebalance_in(server_to_remove)

    # Verify all sgs and accels are still running
    cluster = Cluster()
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.rebalance
def test_server_goes_down_sanity(params_from_base_test_setup):
    """
    1. Start with a two node couchbase server cluster
    2. Starting adding docs
    3. Kill one of the server nodes and signal completion
    4. Stop adding docs
    5. Verify that that the expected docs are present and in the changes feed.
    6. Start server again and add to cluster
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    cluster_helper = ClusterKeywords()

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper.reset_cluster(cluster_config=cluster_config,
                                 sync_gateway_config=sg_conf_path)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    admin_sg = topology["sync_gateways"][0]["admin"]
    sg_url = topology["sync_gateways"][0]["public"]
    coucbase_servers = topology["couchbase_servers"]

    cbs_one_url = coucbase_servers[0]
    cbs_two_url = coucbase_servers[1]

    log_info("Running: 'test_server_goes_down_sanity'")
    log_info("cluster_config: {}".format(cluster_config))
    log_info("admin_sg: {}".format(admin_sg))
    log_info("sg_url: {}".format(sg_url))
    log_info("cbs_one_url: {}".format(cbs_one_url))
    log_info("cbs_two_url: {}".format(cbs_two_url))

    sg_db = "db"
    num_docs = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    main_server = CouchbaseServer(cbs_one_url)
    flakey_server = CouchbaseServer(cbs_two_url)

    client.create_user(admin_sg, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg, sg_db, sg_user_name)

    # Stop second server
    # TODO: Make async
    flakey_server.stop()

    # Wait 30 seconds for auto failover to trigger
    log_info("Waiting 30 seconds to allow auto failover to kick in ...")
    time.sleep(30)

    # Try to add 100 docs in a loop until all succeed, if the never do, fail with timeout
    errors = num_docs
    timeout = 15
    start = time.time()

    while errors != 0:
        # Fail tests if all docs do not succeed before timeout
        if (time.time() - start) > timeout:
            # Bring server back up before failing the test
            flakey_server.start()
            main_server.rebalance_in(flakey_server)
            raise TimeoutError("Failed to successfully put docs before timeout")

        docs, errors = client.add_docs(url=sg_url, db=sg_db, number=num_docs, id_prefix=str(uuid.uuid4()), auth=session, allow_errors=True)
        errors = len(errors)
        log_info("Seeing: {} errors".format(errors))

        time.sleep(1)

    # TODO: Verify GET (bulk) of docs
    # TODO: Verify _changes (basic) feed

    # Test succeeded without timeout, bring server back into topology
    flakey_server.start()
    main_server.recover(flakey_server)
    main_server.rebalance_in(coucbase_servers, flakey_server)

    # Make sure all docs were not added before server was
    log_info("test_server_goes_down_sanity complete!")
