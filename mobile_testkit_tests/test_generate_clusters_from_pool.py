# This is to test the generate_clusters_from_pool.py
# to ensure that it works with and without the
# ip_to_node_type mapping in pool.json
# Uses mock_pool_ips.json and mock_pool_ip_to_node_type.json
# under test_data
# cluster configs will be output to mobile-testkit/resources/cluster_configs

import os
import pytest
import configparser
import json

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool

def test_generate_clusters_from_pool_ips():
    # Function to test pool.json with only IPs
    cwd = os.getcwd()
    TEST_DATA = cwd + "/mobile_testkit_tests/test_data"
    IPS_POOL_FILE = TEST_DATA + "/mock_pool_ips.json"
    CLUSTER_CONFIG_DIR = TEST_DATA + "/cluster_configs"

    # Clear the cluster_configs folder if there are any files
    # Else create a new folder
    if os.path.exists(CLUSTER_CONFIG_DIR):
        os.chdir(CLUSTER_CONFIG_DIR)
        filesToRemove = [f for f in os.listdir(CLUSTER_CONFIG_DIR)]
        for f in filesToRemove:
            os.unlink(f)

        os.chdir(cwd)
    else:
        os.mkdir(CLUSTER_CONFIG_DIR)

    # Run tests with mock_pool_ips.json for backward compatibility
    generate_clusters_from_pool(IPS_POOL_FILE)

    # Verification
    # mock_pool_ips.json will generate 22 files ansible+json
    assert len([name for name in os.listdir(CLUSTER_CONFIG_DIR)])== 22

    # We will check 2 files for content 1cbs/1cbs.json
    config = configparser.ConfigParser()
    config.read(CLUSTER_CONFIG_DIR + "/1cbs")

    # Check only 1 couchbase server is configured
    cbs = config["couchbase_servers"]
    pool = config["pool"]
    sgs = config["sync_gateways"]
    sga = config["sg_accels"]
    lg = config["load_generators"]
    lb = config["load_balancers"]

    assert len(cbs) == 1
    assert len(pool) == 6
    assert len(sgs) == 0
    assert len(sga) == 0
    assert len(lg) == 0
    assert len(lb) == 0

    # Load the json cluster config
    with open(CLUSTER_CONFIG_DIR + "/1cbs.json") as data_file:
        data = json.load(data_file)

    assert len(data["couchbase_servers"]) == 1
    assert len(data["hosts"]) == 6
    assert len(data["sync_gateways"]) == 0
    assert len(data["sg_accels"]) == 0
    assert len(data["load_generators"]) == 0
    assert len(data["load_balancers"]) == 0

def test_generate_clusters_from_pool_ip_to_node():
    # Function to test pool.json with IPs and IP to node type mapping
    cwd = os.getcwd()
    TEST_DATA = cwd + "/mobile_testkit_tests/test_data"
    IP_TO_NODE_TYPE_POOL_FILE = TEST_DATA + "/mock_pool_ip_to_node_type.json"
    CLUSTER_CONFIG_DIR = TEST_DATA + "/cluster_configs"

    # Clear the cluster_configs folder if there are any files
    # Else create a new folder
    if os.path.exists(CLUSTER_CONFIG_DIR):
        os.chdir(CLUSTER_CONFIG_DIR)
        filesToRemove = [f for f in os.listdir(CLUSTER_CONFIG_DIR)]
        for f in filesToRemove:
            os.unlink(f)

        os.chdir(cwd)
    else:
        os.mkdir(CLUSTER_CONFIG_DIR)

    # Run tests with mock_pool_ips.json for backward compatibility
    generate_clusters_from_pool(IP_TO_NODE_TYPE_POOL_FILE)

    # Verification
    # mock_pool_ip_to_node_type.json will generate 18 files ansible+json
    assert len([name for name in os.listdir(CLUSTER_CONFIG_DIR)])== 18

    # We will check 2 files for content 1cbs/1cbs.json
    config = configparser.ConfigParser()
    config.read(CLUSTER_CONFIG_DIR + "/1cbs")

    # Check only 1 couchbase server is configured in 1cbs
    cbs = config["couchbase_servers"]
    pool = config["pool"]
    sgs = config["sync_gateways"]
    sga = config["sg_accels"]
    lg = config["load_generators"]
    lb = config["load_balancers"]

    # Load the mock_pool_ip_to_node_type.json
    with open(IP_TO_NODE_TYPE_POOL_FILE) as pool_data_file:
        pool_data = json.load(pool_data_file)

    assert len(cbs) == 1
    assert len(pool) == 6
    assert len(sgs) == 0
    assert len(sga) == 0
    assert len(lg) == 0
    assert len(lb) == 0

    # Couchbase_server IP from the 1cbs
    cbs_ip = config["couchbase_servers"]["cb1 ansible_host"]

    # Verify that the IP from 1cbs is actually a defined as
    # a couchbase_servers in mock_pool_ip_to_node_type.json
    assert pool_data["ip_to_node_type"][cbs_ip] == "couchbase_servers"

    # Check only 1 couchbase server is configured in 1cbs.json
    with open(CLUSTER_CONFIG_DIR + "/1cbs.json") as data_file:
        data = json.load(data_file)

    assert len(data["couchbase_servers"]) == 1
    assert len(data["hosts"]) == 6
    assert len(data["sync_gateways"]) == 0
    assert len(data["sg_accels"]) == 0
    assert len(data["load_generators"]) == 0
    assert len(data["load_balancers"]) == 0

    # Couchbase_server IP from the 1cbs.json
    cbs_ip = data["couchbase_servers"][0]["ip"]

    # Verify that the IP from 1cbs.json is actually a defined as
    # a couchbase_servers in mock_pool_ip_to_node_type.json
    assert pool_data["ip_to_node_type"][cbs_ip] == "couchbase_servers"
