'''
Created on 27-Dec-2017

@author: hemant
'''
import os
import pytest
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.constants import CLUSTER_CONFIGS_DIR
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient

def test_upgrade():
    os.chdir("/Users/hemant/couchbase/couchbase/mobile-testkit")
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    sg_config = sync_gateway_config_path_for_mode("testfest_todo", "cc")
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    sg_client = MobileRestClient()
    sg_url = "http://172.16.1.163:4985/"
    sg_blip_url = "blip://172.16.1.163:4985/"
    sg_client.create_user(sg_url, "db", "upgradetest", "password", ["ABC"])