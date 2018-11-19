'''
Created on 03-Jan-2018

@author: hemant
'''
import os
from libraries.testkit.cluster import Cluster
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.ClusterKeywords import ClusterKeywords
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords.couchbaseserver import CouchbaseServer


def test_reset():
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    cluster_utils = ClusterKeywords(cluster_config)
    sg_config = "resources/sync_gateway_configs/sync_gateway_travel_sample_cc.json"
    server_version = "6.0.1-1963"
    sync_gateway_version = "2.1.1"
    persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)
    persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sync_gateway_version)
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', 0)
    cluster = Cluster(cluster_config)
    cluster.reset(sg_config)


def test_provision():
    
    cluster_config = "{}/base_{}".format(CLUSTER_CONFIGS_DIR, "di")
    cluster_utils = ClusterKeywords(cluster_config)
    sg_config = "resources/sync_gateway_configs/sync_gateway_travel_sample_di.json"
    server_version = "6.0.1-1963"
    sync_gateway_version = "2.1.1"
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

def test_rebalance_cluster():
    cluster_config = "{}/multiple_servers_{}".format(CLUSTER_CONFIGS_DIR, "cc")
    os.environ["CLUSTER_CONFIG"] = cluster_config
    cluster = Cluster(config=cluster_config)
    if len(cluster.servers) < 2:
        raise Exception("Please provide at least 3 servers")

    server_urls = []
    for server in cluster.servers:
        server_urls.append(server.url)
    primary_server = cluster.servers[0]
    servers = cluster.servers[1:]

    for server in servers:
        print "Rebalance out server: {}".format(server.host)
        primary_server.rebalance_out(server_urls, server)
        print "Adding Server back {}".format(server.host)
        primary_server.add_node(server)
        print "Rebalance in server: {}".format(server.host)
        primary_server.rebalance_in(server_urls, server)
