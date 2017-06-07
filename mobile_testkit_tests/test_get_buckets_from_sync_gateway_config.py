# This is to test the get_buckets_from_sync_gateway_config
# method in install_sync_gateway.py
# to ensure that the expected buckets are returned

import os
import pytest

from libraries.provision.install_sync_gateway import get_buckets_from_sync_gateway_config


@pytest.mark.parametrize("sync_gateway_path, buckets", [
    ("testfest_todo_di.json", ['data-bucket', 'index-bucket']),
    ("default.json", []),
    ("dist_index_config_local.json", ['data-bucket', 'cbgt-bucket', 'index-bucket']),
    ("grocery_sync_conf.json", []),
    ("log_rotation_cc.json", ['data-bucket']),
    ("log_rotation_di.json", ['data-bucket', 'index-bucket']),
    ("missing_num_shards_di.json", ['data-bucket', 'index-bucket']),
    ("multiple_dbs_shared_data_shared_index_cc.json", ['data-bucket']),
    ("multiple_dbs_shared_data_shared_index_di.json", ['data-bucket', 'index-bucket']),
    ("multiple_dbs_unique_data_unique_index_cc.json", ['data-bucket', 'data-bucket-2']),
    ("multiple_dbs_unique_data_unique_index_di.json", ['index-bucket-2', 'index-bucket', 'data-bucket', 'data-bucket-2']),
    ("reject_all_cc.json", ['data-bucket']),
    ("reject_all_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_bucketshadow_cc.json", ['data-bucket', 'source-bucket']),
    ("sync_gateway_bucketshadow_di.json", ['source-bucket', 'data-bucket', 'index-bucket']),
    ("sync_gateway_bucketshadow_low_revs_cc.json", ['data-bucket', 'source-bucket']),
    ("sync_gateway_bucketshadow_low_revs_di.json", ['source-bucket', 'data-bucket', 'index-bucket']),
    ("sync_gateway_channel_cache_cc.json", ['data-bucket']),
    ("sync_gateway_channel_cache_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_default_cc.json", ['data-bucket']),
    ("sync_gateway_default_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_default_functional_tests_cc.json", ['data-bucket']),
    ("sync_gateway_default_functional_tests_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_default_functional_tests_revslimit50_cc.json", ['data-bucket']),
    ("sync_gateway_default_functional_tests_revslimit50_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_default_low_revs_cc.json", ['data-bucket']),
    ("sync_gateway_default_low_revs_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_gzip_cc.json", ['data-bucket']),
    ("sync_gateway_gzip_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_openid_connect_cc.json", ['data-bucket']),
    ("sync_gateway_openid_connect_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_openid_connect_unsigned_cc.json", ['data-bucket']),
    ("sync_gateway_openid_connect_unsigned_di.json", ['data-bucket', 'index-bucket']),
    ("sync_gateway_sg_replicate_cc.json", ['data-bucket-1', 'data-bucket-2']),
    ("sync_gateway_sg_replicate_continuous_cc.json", ['data-bucket-1', 'data-bucket-2']),
    ("sync_gateway_sg_replicate_continuous_di.json", ['index-bucket-2', 'data-bucket-1', 'index-bucket-1', 'data-bucket', 'data-bucket-2']),
    ("sync_gateway_sg_replicate_di.json", ['index-bucket-2', 'data-bucket-1', 'index-bucket-1', 'data-bucket', 'data-bucket-2']),
    ("sync_gateway_todolite.json", ['data-bucket', 'cbgt-bucket', 'index-bucket']),
    ("webhooks/webhook_offline_cc.json", ['data-bucket']),
    ("webhooks/webhook_offline_di.json", ['data-bucket', 'index-bucket']),
    ("testfest_todo_di.json", ['data-bucket', 'index-bucket']),
    ("todolite.json", ['data-bucket']),
])
def test_get_buckets_from_sync_gateway_config(sync_gateway_path, buckets):
    cwd = os.getcwd()
    sync_gateway_configs_folder = cwd + "/resources/sync_gateway_configs/"

    # Run tests with mock_pool_ips.json for backward compatibility
    bucket_list = get_buckets_from_sync_gateway_config(sync_gateway_configs_folder + sync_gateway_path)

    # Verification
    # mock_pool_ips.json will generate 22 files ansible+json
    print bucket_list
    print buckets
    assert bucket_list == buckets
