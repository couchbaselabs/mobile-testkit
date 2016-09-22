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
from testsuites.syncgateway.functional.shared.test_longpoll import longpoll_changes_parametrized
from testsuites.syncgateway.functional.shared.test_longpoll import longpoll_changes_sanity
from testsuites.syncgateway.functional.shared.test_multiple_dbs import multiple_db_unique_data_bucket_unique_index_bucket
from testsuites.syncgateway.functional.shared.test_multiple_dbs import multiple_db_single_data_bucket_single_index_bucket
from testsuites.syncgateway.functional.shared.test_multiple_users_multiple_channels_multiple_revisions import mulitple_users_mulitiple_channels_mulitple_revisions
from testsuites.syncgateway.functional.shared.test_roles import roles_sanity
from testsuites.syncgateway.functional.shared.test_seq import seq
from testsuites.syncgateway.functional.shared.test_single_user_single_channel_doc_updates import single_user_single_channel_doc_updates
from testsuites.syncgateway.functional.shared.test_sync import issue_1524
from testsuites.syncgateway.functional.shared.test_sync import sync_access_sanity
from testsuites.syncgateway.functional.shared.test_sync import sync_channel_sanity
from testsuites.syncgateway.functional.shared.test_sync import sync_role_sanity
from testsuites.syncgateway.functional.shared.test_sync import sync_sanity
from testsuites.syncgateway.functional.shared.test_sync import sync_sanity_backfill
from testsuites.syncgateway.functional.shared.test_sync import sync_require_roles
from testsuites.syncgateway.functional.shared.test_users_channels import multiple_users_multiple_channels
from testsuites.syncgateway.functional.shared.test_users_channels import muliple_users_single_channel
from testsuites.syncgateway.functional.shared.test_users_channels import single_user_multiple_channels
from testsuites.syncgateway.functional.shared.test_users_channels import single_user_single_channel


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 1, 5000, 1),
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 50, 5000, 1),
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 50, 10, 10),
    ("{}/sync_gateway_default_functional_tests_revslimit50_cc.json".format(SYNC_GATEWAY_CONFIGS), 50, 50, 1000)
])
def test_continuous_changes_parametrized(setup_1sg_1cbs_test, sg_conf, num_users, num_docs, num_revisions):
    continuous_changes_parametrized(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_users=num_users,
        num_docs=num_docs,
        num_revisions=num_revisions
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 10)
])
def test_continuous_changes_sanity(setup_1sg_1cbs_test, sg_conf, num_docs, num_revisions):
    continuous_changes_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_revisions=num_revisions
    )



@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_online_default_rest(setup_1sg_1cbs_test, sg_conf, num_docs):
    online_default_rest(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf, num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_offline_false_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_offline_false_config_rest(setup_1sg_1cbs_test, sg_conf, num_docs):
    offline_false_config_rest(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_online_to_offline_check_503(setup_1sg_1cbs_test, sg_conf, num_docs):
    online_to_offline_check_503(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000)
])
def test_online_to_offline_changes_feed_controlled_close_continuous(setup_1sg_1cbs_test, sg_conf, num_docs):
    online_to_offline_changes_feed_controlled_close_continuous(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_users", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000, 40)
])
def test_online_to_offline_continous_changes_feed_controlled_close_sanity_mulitple_users(setup_1sg_1cbs_test, sg_conf, num_docs, num_users):
    online_to_offline_continous_changes_feed_controlled_close_sanity_mulitple_users(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_users=num_users
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000)
])
def test_online_to_offline_changes_feed_controlled_close_longpoll_sanity(setup_1sg_1cbs_test, sg_conf, num_docs):
    online_to_offline_changes_feed_controlled_close_longpoll_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_users", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000, 40)
])
def test_online_to_offline_longpoll_changes_feed_controlled_close_sanity_mulitple_users(setup_1sg_1cbs_test, sg_conf, num_docs, num_users):
    online_to_offline_longpoll_changes_feed_controlled_close_sanity_mulitple_users(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_users=num_users
    )

@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000)
])
def test_online_to_offline_changes_feed_controlled_close_longpoll(setup_1sg_1cbs_test, sg_conf, num_docs):
    online_to_offline_changes_feed_controlled_close_longpoll(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )



@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_offline_true_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_offline_true_config_bring_online(setup_1sg_1cbs_test, sg_conf, num_docs):
    offline_true_config_bring_online(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_dcp_cc.json".format(SYNC_GATEWAY_CONFIGS), 100),
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_db_offline_tap_loss_sanity(setup_1sg_1cbs_test, sg_conf, num_docs):
    db_offline_tap_loss_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )

@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_default_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_db_delayed_online(setup_1sg_1cbs_test, sg_conf, num_docs):
    db_delayed_online(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_cc.json".format(SYNC_GATEWAY_CONFIGS), 100)
])
def test_multiple_dbs_unique_buckets_lose_tap(setup_1sg_1cbs_test, sg_conf, num_docs):
    multiple_dbs_unique_buckets_lose_tap(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_revs", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 5000, 1),
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 50, 100)
])
def test_longpoll_changes_parametrized(setup_1sg_1cbs_test, sg_conf, num_docs, num_revs):
    longpoll_changes_parametrized(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_revisions=num_revs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_revs", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 10),
])
def test_longpoll_changes_sanity(setup_1sg_1cbs_test, sg_conf, num_docs, num_revs):
    longpoll_changes_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_revisions=num_revs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_docs_per_user", [
    ("{}/multiple_dbs_unique_data_unique_index_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 500),
])
def test_multiple_db_unique_data_bucket_unique_index_bucket(setup_1sg_1cbs_test, sg_conf, num_users, num_docs_per_user):
    multiple_db_unique_data_bucket_unique_index_bucket(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_users=num_users,
        num_docs_per_user=num_docs_per_user
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_docs_per_user", [
    ("{}/multiple_dbs_shared_data_shared_index_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 500),
])
def test_multiple_db_single_data_bucket_single_index_bucket(setup_1sg_1cbs_test, sg_conf, num_users, num_docs_per_user):
    multiple_db_single_data_bucket_single_index_bucket(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_users=num_users,
        num_docs_per_user=num_docs_per_user
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_channels,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 3, 10, 10),
])
def test_mulitple_users_mulitiple_channels_mulitple_revisions(setup_1sg_1cbs_test, sg_conf, num_users, num_channels, num_docs, num_revisions):
    mulitple_users_mulitiple_channels_mulitple_revisions(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_users=num_users,
        num_channels=num_channels,
        num_docs=num_docs,
        num_revisions=num_revisions
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.role
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_roles_sanity(setup_1sg_1cbs_test, sg_conf):
    roles_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_users,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 10, 500, 1),
])
def test_seq(setup_1sg_1cbs_test, sg_conf, num_users, num_docs, num_revisions):
    seq(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_users=num_users,
        num_docs=num_docs,
        num_revisions=num_revisions
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs,num_revisions", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS), 100, 100),
])
def test_single_user_single_channel_doc_updates(setup_1sg_1cbs_test, sg_conf, num_docs, num_revisions):
    single_user_single_channel_doc_updates(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs,
        num_revisions=num_revisions
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf,num_docs", [
    ("{}/custom_sync/grant_access_one_cc.json".format(SYNC_GATEWAY_CONFIGS), 10),
])
def test_issue_1524(setup_1sg_1cbs_test, sg_conf, num_docs):
    issue_1524(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf,
        num_docs=num_docs
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.access
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_custom_sync_access_sanity_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_access_sanity(setup_1sg_1cbs_test, sg_conf):
    sync_access_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.channel
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/custom_sync/sync_gateway_custom_sync_channel_sanity_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_channel_sanity(setup_1sg_1cbs_test, sg_conf):
    sync_channel_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.role
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/custom_sync/sync_gateway_custom_sync_role_sanity_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_role_sanity(setup_1sg_1cbs_test, sg_conf):
    sync_role_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/custom_sync/sync_gateway_custom_sync_one_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_sanity(setup_1sg_1cbs_test, sg_conf):
    sync_sanity(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/custom_sync/sync_gateway_custom_sync_one_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_sanity_backfill(setup_1sg_1cbs_test, sg_conf):
    sync_sanity_backfill(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.role
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/custom_sync/sync_gateway_custom_sync_require_roles_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_sync_require_roles(setup_1sg_1cbs_test, sg_conf):
    sync_require_roles(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_multiple_users_multiple_channels(setup_1sg_1cbs_test, sg_conf):
    multiple_users_multiple_channels(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_muliple_users_single_channel(setup_1sg_1cbs_test, sg_conf):
    muliple_users_single_channel(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_single_user_multiple_channels(setup_1sg_1cbs_test, sg_conf):
    single_user_multiple_channels(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
@pytest.mark.parametrize("sg_conf", [
    ("{}/sync_gateway_default_functional_tests_cc.json".format(SYNC_GATEWAY_CONFIGS)),
])
def test_single_user_single_channel(setup_1sg_1cbs_test, sg_conf):
    single_user_single_channel(
        cluster_conf=setup_1sg_1cbs_test["cluster_config"],
        sg_conf=sg_conf
    )





