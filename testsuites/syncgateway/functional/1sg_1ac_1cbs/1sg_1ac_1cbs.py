import pytest
import os

from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging

from testsuites.syncgateway.functional.shared.test_continuous import continuous_changes_parametrized
from testsuites.syncgateway.functional.shared.test_continuous import continuous_changes_sanity
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_default_rest
from testsuites.syncgateway.functional.shared.test_db_online_offline import offline_false_config_rest
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_check_503
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_changes_feed_controlled_close_continuous
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_continous_changes_feed_controlled_close_sanity_mulitple_users
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_changes_feed_controlled_close_longpoll_sanity
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_longpoll_changes_feed_controlled_close_sanity_mulitple_users
from testsuites.syncgateway.functional.shared.test_db_online_offline import online_to_offline_changes_feed_controlled_close_longpoll
from testsuites.syncgateway.functional.shared.test_db_online_offline import offline_true_config_bring_online
from testsuites.syncgateway.functional.shared.test_db_online_offline import db_offline_tap_loss_sanity
from testsuites.syncgateway.functional.shared.test_db_online_offline import db_delayed_online
from testsuites.syncgateway.functional.shared.test_db_online_offline import multiple_dbs_unique_buckets_lose_tap


# This will be called once for the first test in the file.
# After all the tests have completed the function will execute everything after the yield
@pytest.fixture(scope="module")
def setup_1sg_1ac_1cbs_suite(request):
    log_info("Setting up client sync_gateway suite ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    # Set the CLUSTER_CONFIG environment variable to 1sg_1ac_1cbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("1sg_1ac_1cbs")

    cluster_helper.provision_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
    )

    yield

    log_info("Tearing down suite ...")


# This is called before each test and will yield the cluster config to each test in the file
# After each test, the function will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_1sg_1ac_1cbs_test(request):

    test_name = request.node.name

    # TODO REMOVE!!!!!!
    # cluster_helper = ClusterKeywords()
    # cluster_helper.set_cluster_config("1sg_1ac_1cbs")

    yield {"cluster_config": os.environ["CLUSTER_CONFIG"]}

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(test_name)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS), 1, 5000, 1),
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS), 50, 5000, 1),
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS), 50, 10, 10),
    ("{}/sync_gateway_default_functional_tests_revslimit50_di.json".format(SYNC_GATEWAY_CONFIGS), 50, 50, 1000)
])
def test_continuous_changes_parametrized_di(setup_1sg_1ac_1cbs_test, sg_conf, num_users, num_docs, num_revisions):
    continuous_changes_parametrized(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_users=num_users, num_docs=num_docs, num_revisions=num_revisions)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS), 10, 10)
])
def test_continuous_changes_sanity_di(setup_1sg_1ac_1cbs_test, sg_conf, num_docs, num_revisions):
    continuous_changes_sanity(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_docs=num_docs, num_revisions=num_revisions)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_online_default_rest(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
    online_default_rest(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_docs=num_docs)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_offline_false_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_offline_false_config_rest(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
    offline_false_config_rest(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_docs=num_docs)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_online_to_offline_check_503(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
    online_to_offline_check_503(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_docs=num_docs)


# @pytest.mark.sanity
# @pytest.mark.syncgateway
# @pytest.mark.onlineoffline
# @pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
# @pytest.mark.parametrize("sg_conf,num_docs", [
#     ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 5000)
# ])
# def test_online_to_offline_changes_feed_controlled_close_continuous(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
#     online_to_offline_changes_feed_controlled_close_continuous(cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"], sg_conf=sg_conf, num_docs=num_docs)

@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_users", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 5000, 40)
])
def test_online_to_offline_continous_changes_feed_controlled_close_sanity_mulitple_users(setup_1sg_1ac_1cbs_test, sg_conf, num_docs, num_users):
    online_to_offline_continous_changes_feed_controlled_close_sanity_mulitple_users(
        cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_users=num_users
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 5000)
])
def test_online_to_offline_changes_feed_controlled_close_longpoll_sanity(setup_1sg_1ac_1cbs_test, sg_conf, num_docs, num_users):
    online_to_offline_changes_feed_controlled_close_longpoll_sanity(
        cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_users", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 5000, 40)
])
def test_online_to_offline_longpoll_changes_feed_controlled_close_sanity_mulitple_users(setup_1sg_1ac_1cbs_test, sg_conf, num_docs, num_users):
    online_to_offline_longpoll_changes_feed_controlled_close_sanity_mulitple_users(
        cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_users=num_users
    )

# @pytest.mark.sanity
# @pytest.mark.syncgateway
# @pytest.mark.onlineoffline
# @pytest.mark.changes
# @pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
# @pytest.mark.parametrize("sg_conf,num_docs", [
#     ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 5000)
# ])
# def test_online_to_offline_changes_feed_controlled_close_longpoll(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
#     online_to_offline_changes_feed_controlled_close_longpoll(
#         cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
#         sg_conf=sg_conf,
#         num_docs=num_docs,
#     )

# @pytest.mark.sanity
# @pytest.mark.syncgateway
# @pytest.mark.onlineoffline
# @pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
# @pytest.mark.parametrize("sg_conf,num_docs", [
#     ("{}/bucket_online_offline/bucket_online_offline_offline_true_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
# ])
# def test_offline_true_config_bring_online(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
#     offline_true_config_bring_online(
#         cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
#         sg_conf=sg_conf,
#         num_docs=num_docs,
#     )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_db_offline_tap_loss_sanity(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
    db_offline_tap_loss_sanity(
        cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )

# @pytest.mark.sanity
# @pytest.mark.syncgateway
# @pytest.mark.onlineoffline
# @pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
# @pytest.mark.parametrize("sg_conf,num_docs", [
#     ("{}/bucket_online_offline/bucket_online_offline_default_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
# ])
# def test_db_delayed_online(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
#     db_delayed_online(
#         cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
#         sg_conf=sg_conf,
#         num_docs=num_docs,
#     )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
#@pytest.mark.usefixtures("setup_1sg_1ac_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_di.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_multiple_dbs_unique_buckets_lose_tap(setup_1sg_1ac_1cbs_test, sg_conf, num_docs):
    multiple_dbs_unique_buckets_lose_tap(
        cluster_conf=setup_1sg_1ac_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )