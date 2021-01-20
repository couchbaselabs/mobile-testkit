""" Setup for Sync Gateway system tests """

import pytest
import os
import json
from pathlib import Path

from libraries.NetworkUtils import NetworkUtils
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.tklogging import Logging
from keywords.utils import log_info, clear_resources_pngs
from libraries.testkit import cluster
from keywords.exceptions import LogScanningError


# Add custom arguments for executing tests in this directory
def pytest_addoption(parser):

    parser.addoption("--cbs-endpoints",
                     action="store",
                     help="cbs-endpoints: the couchbase server endpoint list")

    parser.addoption("--server-version",
                     action="store",
                     help="server-version: Couchbase Server version to install (ex. 7.0.0-4170 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--sync-gateway-version",
                     action="store",
                     help="sync-gateway-version: Sync Gateway version to install (ex. 2.8.0-374 or 590c1c31c7e83503eff304d8c0789bdd268d6291)")

    parser.addoption("--collect-logs",
                     action="store_true",
                     help="Collect logs for every test. If this flag is not set, collection will only happen for test failures.")

    parser.addoption("--sgw-endpoints",
                     action="store",
                     help="sgw-endpoints: the sync gateway endpoint list")

    parser.addoption("--up-time",
                     action="store",
                     default="300",
                     help="Specify the no. of seconds to run the system time")

    parser.addoption("--server-seed-docs",
                     action="store",
                     help="server-seed-docs: Number of docs to seed the Couchbase server with")

    parser.addoption("--max-docs",
                     action="store",
                     help="max-doc-size: Max number of docs to run the test with")

    parser.addoption("--num-users",
                     action="store",
                     help="num-users: Number of users to run the simulation with")

    parser.addoption("--create-batch-size",
                     action="store",
                     help="create-batch-size: Number of docs to add in bulk on each POST creation")

    parser.addoption("--create-delay",
                     action="store",
                     help="create-delay: Delay between each bulk POST operation")

    parser.addoption("--update-batch-size",
                     action="store",
                     help="update-batch-size: Number of docs to add in bulk on each POST update")

    parser.addoption("--update-docs-percentage",
                     action="store",
                     help="update-docs-percentage: Percentage of user docs to update on each batch")

    parser.addoption("--update-delay",
                     action="store",
                     help="update-delay: Delay between each bulk POST operation for updates")

    parser.addoption("--changes-delay",
                     action="store",
                     help="changes-delay: Delay between each _changes request")

    parser.addoption("--changes-limit",
                     action="store",
                     help="changes-limit: Amount of docs to return per changes request")


@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    # pytest command line parameters
    cbs_endpoints = request.config.getoption("--cbs-endpoints")
    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    collect_logs = request.config.getoption("--collect-logs")
    sgw_endpoints = request.config.getoption("--sgw-endpoints")
    up_time = request.config.getoption("--up-time")

    server_seed_docs = request.config.getoption("--server-seed-docs")
    max_docs = request.config.getoption("--max-docs")
    num_users = request.config.getoption("--num-users")
    create_batch_size = request.config.getoption("--create-batch-size")
    create_delay = request.config.getoption("--create-delay")
    update_batch_size = request.config.getoption("--update-batch-size")
    update_docs_percentage = request.config.getoption("--update-docs-percentage")
    update_delay = request.config.getoption("--update-delay")
    changes_delay = request.config.getoption("--changes-delay")
    changes_limit = request.config.getoption("--changes-limit")

    cluster_config = set_cluster_config_json(cbs_endpoints, server_version, sgw_endpoints, sync_gateway_version)

    yield {
        "cluster_config": cluster_config,
        "cbs_endpoints": cbs_endpoints,
        "server_version": server_version,
        "sync_gateway_version": sync_gateway_version,
        "sgw_endpoints": sgw_endpoints,
        "collect_logs": collect_logs,
        "up_time": up_time,
        "server_seed_docs": server_seed_docs,
        "max_docs": max_docs,
        "num_users": num_users,
        "create_batch_size": create_batch_size,
        "create_delay": create_delay,
        "update_batch_size": update_batch_size,
        "update_docs_percentage": update_docs_percentage,
        "update_delay": update_delay,
        "changes_delay": changes_delay,
        "changes_limit": changes_limit
    }

    log_info("Tearing down 'params_from_base_suite_setup' ...")
    # Delete png files under resources/data
    clear_resources_pngs()


# This is called before each test and will yield the dictionary to each test that references the method
# as a parameter to the test method
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    cluster_config = params_from_base_suite_setup["cluster_config"]
    cbs_endpoints = params_from_base_suite_setup["cbs_endpoints"]
    server_version = params_from_base_suite_setup["server_version"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    sgw_endpoints = params_from_base_suite_setup["sgw_endpoints"]
    collect_logs = params_from_base_suite_setup["collect_logs"]
    up_time = params_from_base_suite_setup["up_time"]

    server_seed_docs = params_from_base_suite_setup["server_seed_docs"]
    max_docs = params_from_base_suite_setup["max_docs"]
    num_users = params_from_base_suite_setup["num_users"]
    create_batch_size = params_from_base_suite_setup["create_batch_size"]
    create_delay = params_from_base_suite_setup["create_delay"]
    update_batch_size = params_from_base_suite_setup["update_batch_size"]
    update_docs_percentage = params_from_base_suite_setup["update_docs_percentage"]
    update_delay = params_from_base_suite_setup["update_delay"]
    changes_delay = params_from_base_suite_setup["changes_delay"]
    changes_limit = params_from_base_suite_setup["changes_limit"]

    test_name = request.node.name
    log_info("Running test '{}'".format(test_name))

    sg_db_list, sg_url_list, sg_admin_url_list = set_cluster_config_host(sgw_endpoints)

    # This dictionary is passed to each test
    yield {
        "cluster_config": cluster_config,
        "sync_gateway_version": sync_gateway_version,
        "sg_db_list": sg_db_list,
        "sg_url_list": sg_url_list,
        "sg_admin_url_list": sg_admin_url_list,
        "up_time": up_time,
        "server_seed_docs": server_seed_docs,
        "max_docs": max_docs,
        "num_users": num_users,
        "create_batch_size": create_batch_size,
        "create_delay": create_delay,
        "update_batch_size": update_batch_size,
        "update_docs_percentage": update_docs_percentage,
        "update_delay": update_delay,
        "changes_delay": changes_delay,
        "changes_limit": changes_limit
    }

    # Code after the yield will execute when each test finishes
    log_info("Tearing down test '{}'".format(test_name))

    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive("cc")

    # if the test failed or a node is down, pull logs
    logging_helper = Logging()
    if collect_logs or request.node.rep_call.failed or len(errors) != 0:
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)

    assert len(errors) == 0

    # Scan logs
    # SG logs for panic, data race
    # System logs for OOM
    ansible_runner = AnsibleRunner(cluster_config)
    script_name = "{}/utilities/check_logs.sh".format(os.getcwd())
    status = ansible_runner.run_ansible_playbook(
        "check-logs.yml",
        extra_vars={
            "script_name": script_name
        }
    )

    if status != 0:
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)
        raise LogScanningError("Errors found in the logs")


def set_cluster_config_host(sgw_endpoints):
    sgw_list = sgw_endpoints.split(',')

    temp_config = "{}/{}".format(CLUSTER_CONFIGS_DIR, "temp_config")
    config_file_path = Path(temp_config)
    if config_file_path.is_file():
        # file exists, clean up
        os.remove(config_file_path)
    config_file_path.touch()
    f = open(temp_config, "w")
    f.write("[sync_gateways]\n")

    sg_db_list = []
    sg_url_list = []
    sg_admin_url_list = []

    idx = 0
    for sgw in sgw_list:
        idx += 1
        sg_db_list.append("db")
        sg_url_list.append("http://{}:4984".format(sgw))
        sg_admin_url_list.append("http://{}:4985".format(sgw))
        f.write("sg{} ansible_host={}\n".format(idx, sgw))

    f.close()
    os.environ["CLUSTER_CONFIG"] = temp_config
    return sg_db_list, sg_url_list, sg_admin_url_list


def set_cluster_config_json(cbs_endpoints, server_version, sgw_endpoints, sync_gateway_version):
    cbs_list = cbs_endpoints.split(",")
    sgw_list = sgw_endpoints.split(',')
    temp_config = "{}/{}".format(CLUSTER_CONFIGS_DIR, "temp_config")
    config_file_path = Path("{}.json".format(temp_config))
    if config_file_path.is_file():
        # file exists, clean up
        os.remove(config_file_path)
    config_file_path.touch()

    data = {}

    cbs_idx = 0
    sgw_idx = 0

    hosts = []
    couchbase_servers = []
    sync_gateways = []

    for cbs in cbs_list:
        host_data = {}
        cbs_data = {}
        cbs_idx = cbs_idx + 1
        host_data["name"] = "host{}".format(cbs_idx)
        cbs_data["name"] = "cd{}".format(cbs_idx)
        host_data["ip"] = cbs
        cbs_data["ip"] = cbs
        hosts.append(host_data)
        couchbase_servers.append(cbs_data)

    idx = cbs_idx
    for sgw in sgw_list:
        host_data = {}
        sgw_data = {}
        idx = idx + 1
        sgw_idx = sgw_idx + 1
        host_data["name"] = "host{}".format(idx)
        sgw_data["name"] = "sg{}".format(sgw_idx)
        host_data["ip"] = sgw
        sgw_data["ip"] = sgw
        hosts.append(host_data)
        sync_gateways.append(sgw_data)

    data["hosts"] = hosts
    data["couchbase_servers"] = couchbase_servers
    data["sync_gateways"] = sync_gateways

    data["sg_accels"] = []
    data["load_generators"] = [],
    data["load_balancers"] = [],

    env = {}
    env["cbs_ssl_enabled"] = False
    env["sync_gateway_version"] = sync_gateway_version
    env["server_version"] = server_version
    env["xattrs_enabled"] = True
    env["sg_lb_enabled"] = False
    env["ipv6_enabled"] = False
    env["x509_certs"] = False
    env["delta_sync_enabled"] = True
    env["two_sg_cluster_lb_enabled"] = False
    env["sync_gateway_ssl"] = False
    env["cbl_log_decoder_platform"] = None
    env["no_conflicts_enabled"] = False
    env["sg_use_views"] = False
    env["sg_platform"] = "centos"
    env["number_replicas"] = 0
    data["environment"] = env

    json_data = json.dumps(data)

    # Writing to temp_config.json
    with open("{}.json".format(temp_config), "w") as f:
        f.write(json_data)

    return temp_config