import pytest
# import time

# from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway
# from keywords import document
# from keywords.utils import host_for_url
# from couchbase.bucket import Bucket
# from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
# from libraries.testkit import cluster
# from concurrent.futures import ThreadPoolExecutor
# from libraries.testkit.prometheus import verify_stat_on_prometheus
# from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import copy_to_temp_conf
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config


@pytest.mark.syncgateway
@pytest.mark.parametrize("group_type", [
    ("default"),
    # ("move")
])
def test_1named_and_default_group(params_from_base_test_setup, group_type):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    Covers #47 on sheet 1
    "1. set up server with bucket1
    2. Set up 1 sgw node with bootstrap config with Group1
    3. Add static config and restart the sgw
    4. Add database config and create db1 , db2 via rest end point
    5. Add new node to the cluster using the same group, Group1
    with bootstrap and static config
    6. Add one more new database config on sgw1
    7. Verify _config end point on sgw2 and verify all configs of sgw1 are inherited to sgw2 including database config added at step 6"
    """

    sg_db = 'db'
    sg_conf_name = "sync_gateway_default"
    sg_obj = SyncGateway()
    # sg_conf_name2 = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    disable_persistent_config = params_from_base_test_setup['disable_persistent_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    # xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    if sync_gateway_version < "3.0.0" or disable_persistent_config:
        pytest.skip('This test can run with sgw version 3.0 and above')
    # 1. Have 2 SGW nodes with disable persistent config
    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'disable_persistent_config', False)
    sg_conf1 = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
    # sg_conf2 = sync_gateway_config_path_for_mode(sg_conf_name2, mode)

    # sg_client = MobileRestClient()
    cluster_utils = ClusterKeywords(cluster_conf)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    # cbs_url = cluster_topology['couchbase_servers'][0]
    # sg_one_url = cluster_topology["sync_gateways"][0]["public"]
    sg_two_url = cluster_topology["sync_gateways"][1]["public"]
    # cbs_host = host_for_url(cbs_url)
    cbs_cluster = Cluster(config=cluster_conf)

    # 2. have default group id on one node and named group in another node
    cbs_cluster.reset(sg_config_path=sg_conf1)
    sg1 = cbs_cluster.sync_gateways[0]
    # sg_dbs = sg1.admin.get_dbs_from_config()
    # sg_db = sg_dbs[0]
    # sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_conf, sg_conf=sg_conf1, url=sg1.ip,
    #                                            sync_gateway_version=sync_gateway_version, enable_import=True)
    if group_type == "default":
        replaced_group = ""
    else:
        replaced_group = "replaced_group"
    str = '"group_id": "persistent_group1",'
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf1, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, str, replaced_group)
    sg_obj.start_sync_gateways(cluster_config=cluster_conf, url=sg_two_url, config=temp_sg_config)
    sg1_return_db = sg1.admin.get_db_config(sg_db)
    print("sg 1 return db config ", sg1_return_db)
