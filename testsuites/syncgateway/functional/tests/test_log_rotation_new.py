import json
import os
import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway, sync_gateway_config_path_for_mode, load_sync_gateway_config, get_sync_gateway_version
from keywords.utils import log_info, host_for_url
from libraries.testkit.cluster import Cluster
from keywords.exceptions import ProvisioningError
from utilities.cluster_config_utils import load_cluster_config_json, persist_cluster_config_environment_prop, copy_to_temp_conf
from libraries.testkit.admin import Admin


# https://github.com/couchbase/sync_gateway/issues/2222
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_rotation_negative(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test log rotation with negative values for:
        "max_size": -1,
        "maxage": -30,
        "maxbackups": -2
    SG shouldn't start
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    disable_persistent_config = params_from_base_test_setup["disable_persistent_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf, use_config=True)

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    # Read sample sg_conf
    if not disable_persistent_config and sync_gateway_version >= "3.0.0":
        cpc_sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
        data = load_sync_gateway_config(cpc_sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf, sg_conf)
    else:
        data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # set negative values for rotation section
    SG_LOGS = ['sg_debug', 'sg_info', 'sg_warn', 'sg_error']

    for log in SG_LOGS:
        log_section = log.split("_")[1]
        data['logging'][log_section]["rotation"] = {
            "max_size": -1,
            "max_age": -30,
            "max_backups": -2,
            "localtime": True
        }

    # Create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)
    try:
        if not disable_persistent_config and sync_gateway_version >= "3.0.0":
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf, use_config=sg_conf)
        else:
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        if not disable_persistent_config and sync_gateway_version >= "3.0.0":
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf, use_config=True)
        else:
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    # os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")


# https://github.com/couchbase/sync_gateway/issues/2225
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_maxbackups_0(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test with maxbackups=0 that means do not limit the number of backups
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_platform = params_from_base_test_setup["sg_platform"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if sync_gateway_version < "2.1" or sync_gateway_version >= "2.6.0":
        pytest.skip("Continuous logging Test NA for SG < 2.1 and backup config is removed 2.6.0 and up")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf, use_config=True)

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    if sg_platform == "windows":
        json_cluster = load_cluster_config_json(cluster_conf)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

    # Create /tmp/sg_logs
    sg_helper.create_directory(cluster_config=cluster_conf, url=sg_one_url, dir_name="/tmp/sg_logs")

    # Read sample sg_conf
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # Generate log file with almost 1MB
    SG_LOGS = ['sg_debug', 'sg_error', 'sg_info', 'sg_warn']

    for log in SG_LOGS:
        # Generate a log file with size ~1MB to check that backup file not created while 100MB not reached
        file_size = 1 * 1024 * 1024
        file_name = "/tmp/sg_logs/{}.log".format(log)
        log_section = log.split("_")[1]
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)
        # Set maxbackups=0 in config file
        data['logging'][log_section]["rotation"]["max_backups"] = 0

    # Create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    # ~1M MB will be added to log file after requests
    send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform)
    for log in SG_LOGS:
        status, stdout, stderr = remote_executor.execute("ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
        if (log == "sg_debug" or log == "sg_info") and sg_platform != "windows":
            if get_sync_gateway_version(sg_ip)[0] < "2.5":
                assert stdout[0].rstrip() == '2'
            else:
                assert stdout[0].rstrip() == '3'
        else:
            assert stdout[0].rstrip() == '2'

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_logLevel_invalid(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Run SG with non existing logLevel value
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    disable_persistent_config = params_from_base_test_setup["disable_persistent_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf, use_config=True)
    if not disable_persistent_config and sync_gateway_version >= "3.0.0":
        admin = Admin(cluster.sync_gateways[0])
        log_config = {
            "logging": {
                "console": {
                    "log_level": "debugFake"
                }
            }
        }
        try:
            admin.put_config(log_config)
        except Exception as ex:
            assert "500 Server Error: Internal Server Error" in str(ex), "did not throw 500 error with invalid value for log keys"
    else:
        sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

        # read sample sg_conf
        data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

        # 'debugFake' invalid value for logLevel
        data['logging']["console"]["log_level"] = "debugFake"

        temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

        # create temp config file in the same folder as sg_conf
        with open(temp_conf, 'w') as fp:
            json.dump(data, fp, indent=4)

        # Stop sync_gateways
        log_info(">>> Stopping sync_gateway")
        sg_helper = SyncGateway()
        sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)
        try:
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
        except ProvisioningError:
            sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
            # Remove generated conf file
            os.remove(temp_conf)
            return

        # Remove generated conf file
        os.remove(temp_conf)
        pytest.fail("SG shouldn't be started!!!!")


@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_rotated_logs_size_limit(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to check rotated log size limit with 100MB( 1024Mb by default)
    1. Have the sg config rotated_logs_size_limit with 100MB
    2. Start the sgw
    3. Send bunch of requests to sgw to get logs with 100MB size
    4. Verify that log gets rotation once it reach 100MB
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_platform = params_from_base_test_setup["sg_platform"]
    disable_persistent_config = params_from_base_test_setup["disable_persistent_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.5.0":
        pytest.skip("rotated log size limit Test NA for the SGW version below 2.5.0")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf, use_config=True)
    if sg_platform == "windows" or "macos" in sg_platform:
        json_cluster = load_cluster_config_json(cluster_conf)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

    # Create /tmp/sg_logs
    sg_helper.create_directory(cluster_config=cluster_conf, url=sg_one_url, dir_name="/tmp/sg_logs")
    SG_LOGS = ['sg_debug', 'sg_info', 'sg_warn', 'sg_error']

    for log in SG_LOGS:
        file_name = "/tmp/sg_logs/{}.log".format(log)
        file_size = 100 * 1024 * 1024
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    # read sample sg_conf
    if not disable_persistent_config and sync_gateway_version >= "3.0.0":
        cpc_sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
        data = load_sync_gateway_config(cpc_sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf, sg_conf)
    else:
        data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # Set maxsize
    for log in SG_LOGS:
        log_section = log.split("_")[1]
        data['logging'][log_section]["rotation"]["rotated_logs_size_limit"] = 100

    # Create a temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    if sg_platform == "windows":
        sg_logs_dir = "C:\\\\tmp\\\\sg_logs"
    else:
        sg_logs_dir = "/tmp/sg_logs"

    if not disable_persistent_config and sync_gateway_version >= "3.0.0":
        sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf, use_config=sg_conf)
    else:
        sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    SG_LOGS_FILES_NUM = get_sgLogs_fileNum(SG_LOGS, remote_executor, sg_platform, sg_logs_dir)
    # ~1M MB will be added to log file after requests
    send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform)

    for log in SG_LOGS:
        command = "ls {} | grep {} | wc -l".format(sg_logs_dir, log)
        _, stdout, _ = remote_executor.execute(command)
        # A rotated log file should be created with 100MB
        if (log == "sg_debug" or log == "sg_info"):
            if sg_platform == "windows" or "macos" in sg_platform:
                assert stdout[0].strip() == SG_LOGS_FILES_NUM[log]
            else:
                assert int(stdout[0].strip()) == int(SG_LOGS_FILES_NUM[log]) + 1

    for log in SG_LOGS:
        if sg_platform == "windows":
            command = "ls -rt {} | grep {} | grep log.gz | head -1".format(sg_logs_dir, log)
        else:
            command = "ls -rt {}/{}*.gz | head -1".format(sg_logs_dir, log)
        _, stdout, _ = remote_executor.execute(command)
        stdout = stdout[0].strip()
        zip_file = stdout
        if sg_platform == "windows":
            _, stdout, _ = remote_executor.execute("ls -lrt {}\\\\{}".format(sg_logs_dir, zip_file))
            stdout = stdout[0].split(' ')[4]
        else:
            print_variable = "{print $5}"
            command = "ls -lrt {} | awk '{}'".format(zip_file, print_variable)
            _, stdout, _ = remote_executor.execute(command)
            stdout = stdout[0].strip()
        log_size = stdout
        assert int(log_size) > 100000, "rotated log size is not created with 100 MB"

    # Remove generated conf file
    os.remove(temp_conf)


def get_sgLogs_fileNum(SG_LOGS_MAXAGE, remote_executor, sg_platform="centos", sg_logs_dir="/tmp/sg_logs/"):
    SG_LOGS_FILES_NUM = {}
    for log in SG_LOGS_MAXAGE:
        command = "ls {} | grep {} | wc -l".format(sg_logs_dir, log)
        _, stdout, _ = remote_executor.execute(command)
        SG_LOGS_FILES_NUM[log] = stdout[0].strip()

    return SG_LOGS_FILES_NUM


def send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform="centos", num_of_requests=2500):
    if sg_platform == "windows":
        command = "for ((i=1;i <= 2000;i += 1)); do curl -s {}/ABCD/ > /dev/null; done".format(sg_one_url)
        os.system(command)
        command = "for ((i=1;i <= 2000;i += 1)); do curl -s -H 'Accept: application/json' {}/db/ > /dev/null; done".format(sg_admin_url)
        os.system(command)

    elif "macos" in sg_platform:
        command = "for ((i=1;i <= 3000;i += 1)); do curl -s {}/ABCD/ > /dev/null; done".format(sg_one_url)
        os.system(command)
        command = "for ((i=1;i <= 2000;i += 1)); do curl -s -H 'Accept: application/json' {}/db/ > /dev/null; done".format(sg_admin_url)
        os.system(command)
    else:
        remote_executor.execute(
            "for ((i=1;i <= {};i += 1)); do curl -s http://localhost:4984/ABCD/ > /dev/null; done".format(num_of_requests))
        remote_executor.execute(
            "for ((i=1;i <= {};i += 1)); do curl -s -H 'Accept: text/plain' http://localhost:4985/db/ > /dev/null; done".format(num_of_requests))
