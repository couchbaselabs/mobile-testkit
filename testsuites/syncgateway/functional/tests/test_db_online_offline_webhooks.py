import time
import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.web_server import WebServer
from libraries.testkit.parallelize import in_parallel

from keywords.utils import log_info
from keywords.SyncGateway import sync_gateway_config_path_for_mode


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions", [
    ("sync_gateway_webhook", 5, 1, 1, 2),
])
def test_webhooks(params_from_base_test_setup, sg_conf_name, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("Offline tests not supported in Di mode -- see https://github.com/couchbase/sync_gateway/issues/2423#issuecomment-300841425")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_webhooks'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

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


# implements scenarios: 18 and 19
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions", [
    ("sync_gateway_webhook", 5, 1, 1, 2),
])
def test_db_online_offline_webhooks_offline(params_from_base_test_setup, sg_conf_name, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("Offline tests not supported in Di mode -- see https://github.com/couchbase/sync_gateway/issues/2423#issuecomment-300841425")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_db_online_offline_webhooks_offline'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

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
    log_info("Expecting db state {} found db state {}".format("Offline", db_info['state']))
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


# implements scenarios: 21
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions", [
    ("sync_gateway_webhook", 5, 1, 1, 2),
])
def test_db_online_offline_webhooks_offline_two(params_from_base_test_setup, sg_conf_name, num_users, num_channels, num_docs, num_revisions):

    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("Offline tests not supported in Di mode -- see https://github.com/couchbase/sync_gateway/issues/2423#issuecomment-300841425")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_db_online_offline_webhooks_offline_two'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

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

    cluster.servers[0].delete_bucket("data-bucket")

    log_info("Sleeping for 120 seconds...")
    time.sleep(120)

    webhook_events = ws.get_data()
    time.sleep(5)
    log_info("webhook event {}".format(webhook_events))
    last_event = webhook_events[-1]
    assert last_event['state'] == 'offline'

    ws.stop()
