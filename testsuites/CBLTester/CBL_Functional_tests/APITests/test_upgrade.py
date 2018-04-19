'''
Created on 03-Jan-2018

@author: hemant
'''
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.ClusterKeywords import ClusterKeywords
from utilities.cluster_config_utils import persist_cluster_config_environment_prop


def test_upgrade():
    cluster_utils = ClusterKeywords()
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    cluster_utils.set_cluster_config(cluster_config.split("/")[-1])
    sg_config = "resources/sync_gateway_configs/testfest_todo_cc.json"
    server_version = "5.5.0-2368"
    sync_gateway_version = "2.0.0-832"
    persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sync_gateway_version)
    cluster = Cluster(cluster_config)
    sg_config = "resources/sync_gateway_configs/testfest_todo_cc.json"
    cluster.reset(sg_config)


def test_provision():
    cluster_utils = ClusterKeywords()
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    cluster_utils.set_cluster_config(cluster_config.split("/")[-1])
    sg_config = "resources/sync_gateway_configs/sync_gateway_default_cc.json"
    server_version = "5.5.0-2368"
    sync_gateway_version = "2.1.0-35"
    persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sync_gateway_version)
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', 0)
    cluster_utils.provision_cluster(
        cluster_config=cluster_config,
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config=sg_config)
