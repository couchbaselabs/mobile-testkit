import time
import pytest
import os

from testkit.admin import Admin
from testkit.cluster import Cluster
from testkit.web_server import WebServer
from testkit.parallelize import *

from keywords.utils import log_info
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
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("num_users, num_channels, num_docs, num_revisions", [
    (5, 1, 1, 2),
])
def test_webhooks(setup_1sg_1cbs_test, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = setup_1sg_1cbs_test["cluster_config"]

    log_info("Running 'test_webhooks'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(30)
    ws.stop()
    expected_events = (num_users * num_docs * num_revisions) + (num_users * num_docs)
    received_events = len(ws.get_data())
    log_info("expected_events: {} received_events {}".format(expected_events, received_events))
    assert expected_events == received_events

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


# implements scenarios: 18 and 19
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("num_users, num_channels, num_docs, num_revisions", [
    (5, 1, 1, 2),
])
def test_db_online_offline_webhooks_offline(setup_1sg_1cbs_test, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = setup_1sg_1cbs_test["cluster_config"]

    log_info("Running 'test_db_online_offline_webhooks_offline'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(10)

    admin.take_db_offline("db")
    time.sleep(5)
    db_info = admin.get_db_info("db")
    log_info("Expecting db state {} found db state {}".format("Offline",db_info['state']))
    assert db_info["state"] == "Offline"

    webhook_events = ws.get_data()
    time.sleep(5)
    log_info("webhook event {}".format(webhook_events))
    last_event = webhook_events[-1]
    assert last_event['state'] == 'offline'

    admin.bring_db_online("db")
    time.sleep(5)
    db_info = admin.get_db_info("db")
    log_info("Expecting db state {} found db state {}".format("Online", db_info['state']))
    assert db_info["state"] == "Online"
    webhook_events = ws.get_data()
    last_event = webhook_events[-1]
    assert last_event['state'] == 'online'
    time.sleep(10)
    log_info("webhook event {}".format(webhook_events))


    ws.stop()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


# implements scenarios: 21
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("num_users, num_channels, num_docs, num_revisions", [
    (5, 1, 1, 2),
])
def test_db_online_offline_webhooks_offline_two(setup_1sg_1cbs_test, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = setup_1sg_1cbs_test["cluster_config"]

    log_info("Running 'test_db_online_offline_webhooks_offline_two'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(10)

    status = cluster.servers[0].delete_bucket("data-bucket")
    assert status == 0

    log_info("Sleeping for 120 seconds...")
    time.sleep(120)

    webhook_events = ws.get_data()
    time.sleep(5)
    log_info("webhook event {}".format(webhook_events))
    last_event = webhook_events[-1]
    assert last_event['state'] == 'offline'

    ws.stop()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0

