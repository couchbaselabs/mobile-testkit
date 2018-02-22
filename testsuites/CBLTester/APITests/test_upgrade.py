'''
Created on 03-Jan-2018

@author: hemant
'''
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.ClusterKeywords import ClusterKeywords


def test_upgrade():
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    cluster = Cluster(cluster_config)
    sg_config = "resources/sync_gateway_configs/testfest_todo_cc.json"
    cluster.reset(sg_config)


def test_provision():
    cluster_utils = ClusterKeywords()
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    sg_config = "resources/sync_gateway_configs/testfest_todo_cc.json"
    cluster_utils.provision_cluster(
        cluster_config=cluster_config,
        server_version="5.0.0-3519",
        sync_gateway_version="1.5.1-4",
        sync_gateway_config=sg_config)
