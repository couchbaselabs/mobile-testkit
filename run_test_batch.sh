#!/usr/bin/env python

import subprocess
import os

DEFAULT_SUITE="testsuites/syncgateway/functional/tests/"
TOPOLOGY_SPECIFIC_SUITE="testsuites/syncgateway/functional/topology_specific_tests/"

tests = [

    # Base CC
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_roles_sanity[sync_gateway_default_functional_tests]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_seq[sync_gateway_default_functional_tests-10-500-1]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_single_user_single_channel_doc_updates[sync_gateway_default_functional_tests-100-100]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_attachments_on_docs_rejected_by_sync_function[reject_all]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_issue_1524[custom_sync/grant_access_one-10]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_sync_access_sanity[custom_sync/sync_gateway_custom_sync_access_sanity]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_user_views_sanity[user_views/user_views]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_overloaded_channel_cache[sync_gateway_channel_cache-5000-*-True-50]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_overloaded_channel_cache[sync_gateway_channel_cache-1000-*-True-50]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_overloaded_channel_cache[sync_gateway_channel_cache-1000-ABC-False-50]"},
    {"mode": "cc", "suite":DEFAULT_SUITE, "testname":"test_overloaded_channel_cache[sync_gateway_channel_cache-1000-ABC-True-50]"},

    # Base DI
    {"mode": "di", "suite":DEFAULT_SUITE, "testname":"test_backfill_channel_grant_to_role_longpoll[custom_sync/access-CHANNEL-REST-channels_to_grant0]"},
    {"mode": "di", "suite":DEFAULT_SUITE, "testname":"test_db_offline_tap_loss_sanity[bucket_online_offline/bucket_online_offline_default_dcp-100]"},
    {"mode": "di", "suite":DEFAULT_SUITE, "testname":"test_db_offline_tap_loss_sanity[bucket_online_offline/bucket_online_offline_default-100]"},
    {"mode": "di", "suite":DEFAULT_SUITE, "testname":"test_multiple_dbs_unique_buckets_lose_tap[bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets-100]"},
    {"mode": "di", "suite":DEFAULT_SUITE, "testname":"test_db_online_offline_webhooks_offline_two[sync_gateway_webhook-5-1-1-2]"},

    # Topology specific CC
    {"mode": "cc", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_bucket_shadow_low_revs_limit_repeated_deletes"},
    {"mode": "cc", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_bucket_shadow_low_revs_limit"},
    {"mode": "cc", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_bucket_shadow_multiple_sync_gateways"},
    {"mode": "cc", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_sg_replicate_basic_test"},

    # Topology specific DI
    {"mode": "di", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_server_goes_down_rebuild_channels"},
    {"mode": "di", "suite":TOPOLOGY_SPECIFIC_SUITE, "testname":"test_dcp_reshard_sync_gateway_comes_up[resources/sync_gateway_configs/sync_gateway_default_functional_tests_di.json]"},

]

for test in tests:
    suite = test["suite"] 
    testname = test["testname"]
    mode = test["mode"]

    print "------------------------------------------------- Running test: suite: {}, testname: {}".format(suite, testname)
    
    cmd_args = [
        "pytest", 
        "-s",
        "--mode={}".format(mode),
        "--skip-provisioning",
        "-k",
        testname,
        suite]
    
    cmd = " ".join(cmd_args)
    os.system(cmd)
