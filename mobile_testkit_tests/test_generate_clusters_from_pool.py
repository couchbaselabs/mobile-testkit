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
import shutil

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool


# Fixture for clearing out the cluster configs
@pytest.fixture(scope="function")
def cleanup_folder():
    cwd = os.getcwd()
    test_data = cwd + "/mobile_testkit_tests/test_data"
    cluster_config_dir = test_data + "/cluster_configs"

    # Clear the cluster_configs folder if there are any files
    # Else create a new folder
    if os.path.exists(cluster_config_dir):
        shutil.rmtree(cluster_config_dir)

    os.mkdir(cluster_config_dir)


@pytest.mark.parametrize("cluster_conf, num_couchbase_servers, num_pool, num_sync_gateways, num_sg_accels, num_load_generators, num_load_balancers", [
    ("1cbs", 1, 6, 0, 0, 0, 0), ("1sg_1ac_1cbs_1lgs", 1, 6, 1, 1, 1, 0), ("2sg_1cbs_1lgs", 1, 6, 2, 0, 1, 0),
])
def test_generate_clusters_from_pool_ips(cleanup_folder, cluster_conf, num_couchbase_servers, num_pool, num_sync_gateways, num_sg_accels, num_load_generators, num_load_balancers):
    # Function to test pool.json with only IPs
    cwd = os.getcwd()
    test_data = cwd + "/mobile_testkit_tests/test_data"
    ips_pool_file = test_data + "/mock_pool_ips.json"
    cluster_config_dir = test_data + "/cluster_configs/"

    # Run tests with mock_pool_ips.json for backward compatibility
    generate_clusters_from_pool(ips_pool_file, False)

    # Verification
    # mock_pool_ips.json will generate 38 files ansible+json
    assert len([name for name in os.listdir(cluster_config_dir)]) == 44

    # We will check 2 files for content 1cbs/1cbs.json
    config = configparser.ConfigParser()
    config.read(cluster_config_dir + cluster_conf)

    # Check only 1 couchbase server is configured
    cbs = config["couchbase_servers"]
    pool = config["pool"]
    sgs = config["sync_gateways"]
    sga = config["sg_accels"]
    lg = config["load_generators"]
    lb = config["load_balancers"]

    assert len(cbs) == num_couchbase_servers
    assert len(pool) == num_pool
    assert len(sgs) == num_sync_gateways
    assert len(sga) == num_sg_accels
    assert len(lg) == num_load_generators
    assert len(lb) == num_load_balancers

    # Load the json cluster config json
    with open(cluster_config_dir + cluster_conf + ".json") as data_file:
        data = json.load(data_file)

    assert len(data["couchbase_servers"]) == num_couchbase_servers
    assert len(data["hosts"]) == num_pool
    assert len(data["sync_gateways"]) == num_sync_gateways
    assert len(data["sg_accels"]) == num_sg_accels
    assert len(data["load_generators"]) == num_load_generators
    assert len(data["load_balancers"]) == num_load_balancers


@pytest.mark.parametrize("cluster_conf, num_couchbase_servers, num_pool, num_sync_gateways, num_sg_accels, num_load_generators, num_load_balancers", [
    ("1cbs", 1, 13, 0, 0, 0, 0), ("1sg_1ac_1cbs_1lgs", 1, 13, 1, 1, 1, 0), ("4sg_2ac_3cbs_4lgs", 3, 13, 4, 2, 4, 0),
])
def test_generate_clusters_from_pool_ip_to_node(cleanup_folder, cluster_conf, num_couchbase_servers, num_pool, num_sync_gateways, num_sg_accels, num_load_generators, num_load_balancers):
    # Function to test pool.json with IPs and IP to node type mapping
    cwd = os.getcwd()
    test_data = cwd + "/mobile_testkit_tests/test_data"
    ip_to_node_type_pool_file = test_data + "/mock_pool_ip_to_node_type.json"
    cluster_config_dir = test_data + "/cluster_configs/"

    # Run tests with mock_pool_ips.json for backward compatibility
    generate_clusters_from_pool(ip_to_node_type_pool_file, False)

    # Verification
    # mock_pool_ip_to_node_type.json will generate 42 ansible+json
    assert len([name for name in os.listdir(cluster_config_dir)]) == 44

    # We will check 2 files for content 1cbs/1cbs.json
    config = configparser.ConfigParser()
    config.read(cluster_config_dir + cluster_conf)

    # Check only 1 couchbase server is configured in 1cbs
    cbs = config["couchbase_servers"]
    pool = config["pool"]
    sgs = config["sync_gateways"]
    sga = config["sg_accels"]
    lg = config["load_generators"]
    lb = config["load_balancers"]

    # Load the mock_pool_ip_to_node_type.json
    with open(ip_to_node_type_pool_file) as pool_data_file:
        pool_data = json.load(pool_data_file)

    assert len(cbs) == num_couchbase_servers
    assert len(pool) == num_pool
    assert len(sgs) == num_sync_gateways
    assert len(sga) == num_sg_accels
    assert len(lg) == num_load_generators
    assert len(lb) == num_load_balancers

    # Check Couchbase_server IP from the the cluster config
    for i in range(num_couchbase_servers):
        host_identifier = "cb{} ansible_host".format(i + 1)
        assert host_identifier in config["couchbase_servers"]
        cbs_ip = config["couchbase_servers"][host_identifier]

        # Verify that the IP from cluster config is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][cbs_ip] == "couchbase_servers"

    # Check Sync gateway IP from the the cluster config
    for i in range(num_sync_gateways):
        host_identifier = "sg{} ansible_host".format(i + 1)
        assert host_identifier in config["sync_gateways"]
        sg_ip = config["sync_gateways"][host_identifier]

        # Verify that the IP from cluster config is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][sg_ip] == "sync_gateways"

    # Check load generators IP from the the cluster config
    for i in range(num_load_generators):
        host_identifier = "lg{} ansible_host".format(i + 1)
        assert host_identifier in config["load_generators"]
        lg_ip = config["load_generators"][host_identifier]

        # Verify that the IP from cluster config is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][lg_ip] == "load_generators"

    # Check load balancers IP from the the cluster config
    for i in range(num_load_balancers):
        host_identifier = "lb{} ansible_host".format(i + 1)
        assert host_identifier in config["load_balancers"]
        lb_ip = config["load_generators"][host_identifier]

        # Verify that the IP from cluster config is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][lb_ip] == "load_balancers"

    # Check sg accels IP from the the cluster config
    for i in range(num_sg_accels):
        host_identifier = "ac{} ansible_host".format(i + 1)
        assert host_identifier in config["sg_accels"]
        ac_ip = config["sg_accels"][host_identifier]

        # Verify that the IP from cluster config is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][ac_ip] == "sg_accels"

    # Check the number of couchbase servers configured in the cluster config json
    with open(cluster_config_dir + cluster_conf + ".json") as data_file:
        data = json.load(data_file)

    assert len(data["couchbase_servers"]) == num_couchbase_servers
    assert len(data["hosts"]) == num_pool
    assert len(data["sync_gateways"]) == num_sync_gateways
    assert len(data["sg_accels"]) == num_sg_accels
    assert len(data["load_generators"]) == num_load_generators
    assert len(data["load_balancers"]) == num_load_balancers

    # Check Couchbase_server IP from the cluster config json
    for i in range(num_couchbase_servers):
        cbs_ip = data["couchbase_servers"][i]["ip"]

        # Verify that the IP from 1cbs is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][cbs_ip] == "couchbase_servers"

    # Check sg_accels IP from the cluster config json
    for i in range(num_sg_accels):
        ac_ip = data["sg_accels"][i]["ip"]

        # Verify that the IP from 1cbs is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][ac_ip] == "sg_accels"

    # Check sync gateways IP from the cluster config json
    for i in range(num_sync_gateways):
        sg_ip = data["sync_gateways"][i]["ip"]

        # Verify that the IP from 1cbs is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][sg_ip] == "sync_gateways"

    # Check load_generators IP from the cluster config json
    for i in range(num_load_generators):
        lg_ip = data["load_generators"][i]["ip"]

        # Verify that the IP from 1cbs is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][lg_ip] == "load_generators"

    # Check load_balancers IP from the cluster config json
    for i in range(num_load_balancers):
        lb_ip = data["load_balancers"][i]["ip"]

        # Verify that the IP from 1cbs is actually a defined as
        # a couchbase_servers in mock_pool_ip_to_node_type.json
        assert pool_data["ip_to_node_type"][lb_ip] == "load_balancers"
