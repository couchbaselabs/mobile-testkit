'''
Created on 03-Jan-2018

@author: hemant
'''
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
import pytest

def test_upgrade():
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    cluster = Cluster(cluster_config)
    cluster.reset("resources/sync_gateway_configs/testfest_todo_cc.json")
