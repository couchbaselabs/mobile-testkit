import os
import pytest

from libraries.testkit.config import Config


@pytest.mark.parametrize("sync_gateway_config, buckets, mode", [
    ("testfest_todo_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("default.json", [], "cc"),
    ("dist_index_config_local.json", ['data-bucket', 'cbgt-bucket', 'index-bucket'], "di"),
    ("grocery_sync_conf.json", [], "cc"),
    ("log_rotation_cc.json", ['data-bucket'], "cc"),
    ("log_rotation_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("missing_num_shards_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("multiple_dbs_shared_data_shared_index_cc.json", ['data-bucket'], "cc"),
    ("multiple_dbs_shared_data_shared_index_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("multiple_dbs_unique_data_unique_index_cc.json", ['data-bucket', 'data-bucket-2'], "cc"),
    ("multiple_dbs_unique_data_unique_index_di.json", ['index-bucket-2', 'index-bucket', 'data-bucket', 'data-bucket-2'], "di"),
    ("reject_all_cc.json", ['data-bucket'], "cc"),
    ("reject_all_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_bucketshadow_cc.json", ['data-bucket', 'source-bucket'], "cc"),
    ("sync_gateway_bucketshadow_di.json", ['source-bucket', 'data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_bucketshadow_low_revs_cc.json", ['data-bucket', 'source-bucket'], "cc"),
    ("sync_gateway_bucketshadow_low_revs_di.json", ['source-bucket', 'data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_channel_cache_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_channel_cache_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_default_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_default_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_default_functional_tests_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_default_functional_tests_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_default_functional_tests_revslimit50_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_default_functional_tests_revslimit50_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_default_low_revs_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_default_low_revs_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_gzip_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_gzip_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_openid_connect_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_openid_connect_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_openid_connect_unsigned_cc.json", ['data-bucket'], "cc"),
    ("sync_gateway_openid_connect_unsigned_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("sync_gateway_sg_replicate_cc.json", ['data-bucket-1', 'data-bucket-2'], "cc"),
    ("sync_gateway_sg_replicate_continuous_cc.json", ['data-bucket-1', 'data-bucket-2'], "cc"),
    ("sync_gateway_sg_replicate_continuous_di.json", ['index-bucket-2', 'data-bucket-1', 'index-bucket-1', 'data-bucket', 'data-bucket-2'], "di"),
    ("sync_gateway_sg_replicate_di.json", ['index-bucket-2', 'data-bucket-1', 'index-bucket-1', 'data-bucket', 'data-bucket-2'], "di"),
    ("webhooks/webhook_offline_cc.json", ['data-bucket'], "cc"),
    ("webhooks/webhook_offline_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("testfest_todo_di.json", ['data-bucket', 'index-bucket'], "di"),
    ("todolite.json", ['data-bucket'], "cc"),
])
def test_config_init(sync_gateway_config, buckets, mode):
    cwd = os.getcwd()
    conf_path = cwd + "/resources/sync_gateway_configs/" + sync_gateway_config

    config = Config(conf_path)

    assert config
    assert config.mode == mode
    assert config.bucket_name_set == buckets
