'''
Created on 03-Jan-2018

@author: hemant
'''
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import sync_gateway_config_path_for_mode
import pytest

def test_upgrade():
    mode = "cc"
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
    cluster = Cluster(cluster_config)
    cluster.reset("resources/sync_gateway_configs/sync_gateway_travel_sample_{}.json".format(mode))

def test_provision():
    mode = "di"
    cluster = ClusterKeywords()
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_travel_sample", mode)
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, mode)
    cluster.provision_cluster(
                cluster_config=cluster_config,
                server_version="5.0.0-3519",
                sync_gateway_version="2.0.0-759",
                sync_gateway_config=sg_config
            )