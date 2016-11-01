import time
import pytest
import os

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes

import concurrent
import concurrent.futures
import requests

from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.Logging import Logging


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_1sg_1cbs_test(request):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    yield {"cluster_config": os.environ["CLUSTER_CONFIG"]}

    log_info("Tearing down test '{}'".format(test_name))

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf, num_docs, user_channels, filter, limit", [
    ("{}/sync_gateway_channel_cache_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000, "*", True, 50),
    ("{}/sync_gateway_channel_cache_cc.json".format(SYNC_GATEWAY_CONFIGS), 1000, "*", True, 50),
    ("{}/sync_gateway_channel_cache_cc.json".format(SYNC_GATEWAY_CONFIGS), 1000, "ABC", False, 50),
    ("{}/sync_gateway_channel_cache_cc.json".format(SYNC_GATEWAY_CONFIGS), 1000, "ABC", True, 50),
])
def test_overloaded_channel_cache(setup_1sg_1cbs_test, sg_conf, num_docs, user_channels, filter, limit):

    cluster_conf = setup_1sg_1cbs_test["cluster_config"]

    log_info("Running 'test_overloaded_channel_cache'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using user_channels: {}".format(user_channels))
    log_info("Using filter: {}".format(filter))
    log_info("Using limit: {}".format(limit))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

    target_sg = cluster.sync_gateways[0]

    admin = Admin(target_sg)

    users = admin.register_bulk_users(target_sg, "db", "user", 1000, "password", [user_channels])
    assert len(users) == 1000

    doc_pusher = admin.register_user(target_sg, "db", "abc_doc_pusher", "password", ["ABC"])
    doc_pusher.add_docs(num_docs, bulk=True)

    # Give a few seconds to let changes register
    time.sleep(2)

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:

        changes_requests = []
        errors = []

        for user in users:
            if filter and limit is not None:
                changes_requests.append(executor.submit(user.get_changes, since=0, limit=limit, filter="sync_gateway/bychannel", channels=["ABC"]))
            elif filter and limit is None:
                changes_requests.append(executor.submit(user.get_changes, filter="sync_gateway/bychannel", channels=["ABC"]))
            elif not filter and limit is not None:
                changes_requests.append(executor.submit(user.get_changes, limit=limit))
            elif not filter and limit is None:
                changes_requests.append(executor.submit(user.get_changes))

        for future in concurrent.futures.as_completed(changes_requests):
            changes = future.result()
            if limit is not None:
                assert len(changes["results"]) == 50
            else:
                assert len(changes["results"]) == 5001

        # changes feed should all be successful
        log_info(len(errors))
        assert len(errors) == 0

        if limit is not None:
            # HACK: Should be less than a minute unless blocking on view calls
            end = time.time()
            time_for_users_to_get_all_changes = end - start
            log_info("Time for users to get all changes: {}".format(time_for_users_to_get_all_changes))
            assert time_for_users_to_get_all_changes < 120, "Time to get all changes was greater than a minute: {}s".format(
                time_for_users_to_get_all_changes
            )

        # Sanity check that a subset of users have _changes feed intact
        for i in range(10):
            verify_changes(users[i], expected_num_docs=num_docs, expected_num_revisions=0, expected_docs=doc_pusher.cache)

        # Get sync_gateway expvars
        resp = requests.get(url="http://{}:4985/_expvar".format(target_sg.ip))
        resp.raise_for_status()
        resp_obj = resp.json()

        if user_channels == "*" and num_docs == 5000:
            # "*" channel includes _user docs so the verify_changes will result in 10 view queries
            assert resp_obj["syncGateway_changeCache"]["view_queries"] == 10
        else:
            # If number of view queries == 0 the key will not exist in the expvars
            assert "view_queries" not in resp_obj["syncGateway_changeCache"]

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0
