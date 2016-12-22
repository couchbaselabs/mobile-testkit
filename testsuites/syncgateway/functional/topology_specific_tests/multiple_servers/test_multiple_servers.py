import time

import pytest
import concurrent.futures
import requests.exceptions
import keywords.exceptions

from keywords.exceptions import TimeoutError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import userinfo
from keywords import couchbaseserver

@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.rebalance
@pytest.mark.skip(reason="Failing due to - https://github.com/couchbase/sync_gateway/issues/2173")
def test_rebalance_sanity(params_from_base_test_setup):

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

    cluster_servers = topology["couchbase_servers"]
    cbs_one_url = cluster_servers[0]
    cbs_two_url = cluster_servers[1]

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
    cb_server = couchbaseserver.CouchbaseServer(cbs_one_url)
    server_to_remove = couchbaseserver.CouchbaseServer(cbs_two_url)

    client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    with concurrent.futures.ThreadPoolExecutor(5) as executor:

        # Add docs to sg
        log_info("Adding docs to sync_gateway")
        docs = client.add_docs(sg_one_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        assert len(docs) == num_docs

        # Start updating docs and rebalance out one CBS node
        log_info("Updating docs on sync_gateway")
        update_docs_task = executor.submit(client.update_docs, sg_one_url, sg_db, docs, num_updates, auth=session)

        # Run rebalance in background
        cb_server.rebalance_out(cluster_servers, server_to_remove)

        updated_docs = update_docs_task.result()
        log_info(updated_docs)

    # Verify docs / revisions present
    client.verify_docs_present(sg_one_url, sg_db, updated_docs, auth=session)

    # Verify docs revisions in changes feed
    client.verify_docs_in_changes(sg_one_url, sg_db, updated_docs, auth=session)

    # Rebalance Server back in to the pool
    cb_server.add_node(server_to_remove)
    cb_server.rebalance_in(cluster_servers, server_to_remove)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.failover
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
    main_server = couchbaseserver.CouchbaseServer(cbs_one_url)
    flakey_server = couchbaseserver.CouchbaseServer(cbs_two_url)

    client.create_user(admin_sg, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg, sg_db, sg_user_name)

    # Stop second server
    flakey_server.stop()

    # Try to add 100 docs in a loop until all succeed, if the never do, fail with timeout
    errors = num_docs

    # Wait 30 seconds for auto failover
    # (Minimum value suggested - http://docs.couchbase.com/admin/admin/Tasks/tasks-nodeFailover.html)
    # + 15 seconds to add docs
    timeout = 45
    start = time.time()

    successful_add = False
    while not successful_add:

        # Fail tests if all docs do not succeed before timeout
        if (time.time() - start) > timeout:
            # Bring server back up before failing the test
            flakey_server.start()
            main_server.rebalance_in(coucbase_servers, flakey_server)
            raise TimeoutError("Failed to successfully put docs before timeout")

        try:
            docs = client.add_docs(url=sg_url, db=sg_db, number=num_docs, id_prefix=None, auth=session, channels=channels)

            # If the above add doc does not throw, it was a successfull add.
            successful_add = True
        except requests.exceptions.HTTPError as he:
            log_info("Failed to add docs: {}".format(he))

        log_info("Seeing: {} errors".format(errors))
        time.sleep(1)

    assert len(docs) == 100
    client.verify_docs_present(url=sg_url, db=sg_db, expected_docs=docs, auth=session)

    try:
        client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs, auth=session, polling_interval=5)
    except keywords.exceptions.TimeoutException:
        # timeout verifying docs. Bring server back in to restore topology, then fail
        # Failing due to https://github.com/couchbase/sync_gateway/issues/2197
        flakey_server.start()
        main_server.recover(flakey_server)
        main_server.rebalance_in(coucbase_servers, flakey_server)
        raise keywords.exceptions.TimeoutException("Failed to get all changes")

    # Test succeeded without timeout, bring server back into topology
    flakey_server.start()
    main_server.recover(flakey_server)
    main_server.rebalance_in(coucbase_servers, flakey_server)

    # Make sure all docs were not added before server was
    log_info("test_server_goes_down_sanity complete!")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.failover
def test_server_goes_down_rebuild_channels(params_from_base_test_setup):
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

    admin_user_info = userinfo.UserInfo(
        name="admin",
        password="password",
        channels=["ABC"],
        roles=[]
    )

    seth_user_info = userinfo.UserInfo(
        name="seth",
        password="password",
        channels=["ABC"],
        roles=[]
    )

    client = MobileRestClient()
    main_server = couchbaseserver.CouchbaseServer(cbs_one_url)
    flakey_server = couchbaseserver.CouchbaseServer(cbs_two_url)

    admin_auth = client.create_user(
        admin_sg,
        sg_db,
        admin_user_info.name,
        admin_user_info.password,
        channels=admin_user_info.channels
    )

    client.create_user(
        admin_sg,
        sg_db,
        seth_user_info.name,
        seth_user_info.password,
        channels=seth_user_info.channels
    )
    seth_session = client.create_session(admin_sg, sg_db, seth_user_info.name)

    # allow any user docs to make it to changes
    initial_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=seth_session)

    # push docs from admin
    docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=num_docs,
        id_prefix=None,
        channels=admin_user_info.channels,
        auth=admin_auth
    )

    assert len(docs) == num_docs

    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs, auth=seth_session)
    changes_before_failover = client.get_changes(url=sg_url, db=sg_db, since=initial_changes["last_seq"], auth=seth_session)
    assert len(changes_before_failover["results"]) == num_docs

    # Stop server via 'service stop'
    flakey_server.stop()

    start = time.time()
    while True:
        # Fail tests if all docs do not succeed before timeout
        if (time.time() - start) > 60:
            # Bring server back up before failing the test
            flakey_server.start()
            main_server.recover(flakey_server)
            main_server.rebalance_in(coucbase_servers, flakey_server)
            raise keywords.exceptions.TimeoutError("Failed to rebuild changes")

        try:
            # Poll until failover happens (~30 second)
            client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs, auth=seth_session)
            # changes requests succeeded, exit loop
            break
        except requests.exceptions.HTTPError:
            # Changes will fail until failover of the down server happens. Wait and try again.
            log_info("/db/_changes failed due to server down. Retrying ...")
            time.sleep(1)

    # Verify no new changes
    changes = client.get_changes(
        url=sg_url,
        db=sg_db,
        since=changes_before_failover["last_seq"],
        auth=seth_session,
        feed="normal"
    )
    assert len(changes["results"]) == 0

    # Check that all changes are intact from initial changes request
    changes = client.get_changes(url=sg_url, db=sg_db, since=initial_changes["last_seq"], auth=seth_session)
    assert len(changes["results"]) == num_docs

    coucbase_servers = topology["couchbase_servers"]

    # Test succeeded without timeout, bring server back into topology
    flakey_server.start()
    main_server.recover(flakey_server)
    main_server.rebalance_in(coucbase_servers, flakey_server)
