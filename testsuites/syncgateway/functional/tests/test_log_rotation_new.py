import json
import os
import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway, sync_gateway_config_path_for_mode, load_sync_gateway_config, get_sync_gateway_version
from keywords.utils import log_info, host_for_url
from libraries.testkit.cluster import Cluster
from keywords.exceptions import ProvisioningError
from utilities.cluster_config_utils import load_cluster_config_json


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_rotation_default_values(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to verify default values for rotation section:
    maxsize = 100 MB
    MaxAge = 0(do not limit the number of MaxAge)
    MaxBackups = 0(do not limit the number of backups)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

    # Read the sample sg_conf
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    SG_LOGGING_SECTIONS = ['console', 'error', 'info', 'warn', 'debug']

    # Remove the rotation key from sample config
    for section in SG_LOGGING_SECTIONS:
        del data['logging'][section]["rotation"]

    # Create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    log_info("TEMP_CONF: {}".format(temp_conf))

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    # Create /tmp/sg_logs
    sg_helper.create_directory(cluster_config=cluster_conf, url=sg_one_url, dir_name="/tmp/sg_logs")

    SG_LOGS = ['sg_debug', 'sg_error', 'sg_info', 'sg_warn']
    json_cluster = load_cluster_config_json(cluster_conf)
    sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
    sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)

    for log in SG_LOGS:
        # Generate a log file with size ~94MB to check that backup file not created while 100MB not reached
        file_size = 94 * 1024 * 1024
        file_name = "/tmp/sg_logs/{}.log".format(log)
        log_info("Testing log rotation for {}".format(file_name))
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    # iterate 5 times to verify that every time we get new backup file with ~100MB
    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    for i in xrange(5):
        # ~1M MB will be added to the info/debug/warn log files after the requests
        send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform)

    # Verify num of log files for every log file type
    for log in SG_LOGS:
        file_name = "/tmp/sg_logs/{}.log".format(log)
        _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
        log_info("Checking for {} files for {}".format(i + 1, file_name))
        assert stdout[0].rstrip() == str(i + 1)

        sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

        # Generate an empty log file with size ~100MB
        file_size = 100 * 1024 * 1024
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_invalid_logKeys_string(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Negative test to verify that we are not able start SG when
    logKeys is string
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
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
    cluster.reset(sg_config_path=sg_conf)

    # read sample sg_conf
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # set logKeys as string in config file
    data['logging']["console"]["log_keys"] = "ABCD"
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

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
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_nondefault_logKeys_set(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to verify non default logKeys with any invalid area.
    SG should work even with non existing logging area
    (positive case)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Test NA for SG  > 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # read sample sg_conf
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # "FAKE" not valid area in logging
    data['logging']["console"]["logKeys"] = ["HTTP", "FAKE"]
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

    # Start sync_gateways
    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_maxage_timestamp_ignored(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to verify SG continues to wrile logs in the same file even when
     timestamp for the log file has been changed
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_platform = params_from_base_test_setup["sg_platform"]

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    json_cluster = load_cluster_config_json(cluster_conf)
    sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
    sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

    # Create /tmp/sg_logs
    sg_helper.create_directory(cluster_config=cluster_conf, url=sg_one_url, dir_name="/tmp/sg_logs")

    # generate log file with almost 1MB
    SG_LOGS_MAXAGE = {'sg_debug': 1, 'sg_info': 3, 'sg_warn': 90, 'sg_error': 180}

    for log in SG_LOGS_MAXAGE:
        # Generate a log file with size ~1MB to check that backup file not created while 100MB not reached
        file_size = 1 * 1024 * 1024
        file_name = "/tmp/sg_logs/{}.log".format(log)
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    # Read sample sg_conf
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # Set maxage to the minimum possible number for each log section
    for log in SG_LOGS_MAXAGE:
        log_section = log.split("_")[1]
        data['logging'][log_section]["rotation"]["max_age"] = SG_LOGS_MAXAGE[log]
        # Create temp config file in the same folder as sg_conf
        temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    # ~1M MB will be added to log file after requests
    send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform)

    sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)
    # Get number of logs for each type of log
    SG_LOGS_FILES_NUM = get_sgLogs_fileNum(SG_LOGS_MAXAGE, remote_executor)
    # Change the timestamps for SG logs when SG stopped (Name is unchanged)
    for log in SG_LOGS_MAXAGE:
        file_name = "/tmp/sg_logs/{}.log".format(log)
        remote_executor.execute("sudo touch -d \"{} days ago\" {}".format(SG_LOGS_MAXAGE[log], file_name))

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)

    for log in SG_LOGS_MAXAGE:
        _, stdout, _ = remote_executor.execute("cmd.exe ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
        # Verify that new log file was not created
        assert stdout[0].rstrip() == SG_LOGS_FILES_NUM[log]

    # Remove generated conf file
    os.remove(temp_conf)


# https://github.com/couchbase/sync_gateway/issues/2221
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_rotation_invalid_path(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to check that SG is not started with invalid logFilePath.
    OS specific case. SG should check if path correct on startup
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
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
    cluster.reset(sg_config_path=sg_conf)

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # set non existing logFilePath
    data['logging']["log_file_path"] = "/12345/1231/131231.log"
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

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
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_200mb(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test to check maxsize with value 200MB( 100Mb by default)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_platform = params_from_base_test_setup["sg_platform"]

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    json_cluster = load_cluster_config_json(cluster_conf)
    sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
    sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)

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
        file_size = 199 * 1024 * 1024
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, cluster_hosts["couchbase_servers"][0], cluster_conf)

    # Set maxsize
    for log in SG_LOGS:
        log_section = log.split("_")[1]
        data['logging'][log_section]["rotation"]["maxsize"] = 200

    # Create a temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp, indent=4)

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    SG_LOGS_FILES_NUM = get_sgLogs_fileNum(SG_LOGS, remote_executor)
    # ~1M MB will be added to log file after requests
    send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform)

    for log in SG_LOGS:
        status, stdout, stderr = remote_executor.execute("ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
        # A backup file should be created with 200MB
        assert stdout[0].rstrip() == SG_LOGS_FILES_NUM[log]

    # Remove generated conf file
    os.remove(temp_conf)


# https://github.com/couchbase/sync_gateway/issues/2222
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_rotation_negative(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Test log rotation with negative values for:
        "maxsize": -1,
        "maxage": -30,
        "maxbackups": -2
    SG shouldn't start
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
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
    cluster.reset(sg_config_path=sg_conf)

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    # Read sample sg_conf
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
        sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")


# https://github.com/couchbase/sync_gateway/issues/2225
@pytest.mark.syncgateway
@pytest.mark.logging
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

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster_helper = ClusterKeywords(cluster_conf)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_ip = host_for_url(sg_admin_url)

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("Continuous logging Test NA for SG < 2.1")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]

    json_cluster = load_cluster_config_json(cluster_conf)
    sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
    sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)

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
        assert stdout[0].rstrip() == '2'

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_logLevel_invalid(params_from_base_test_setup, sg_conf_name):
    """
    @summary
    Run SG with non existing logLevel value
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
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
    cluster.reset(sg_config_path=sg_conf)

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


def get_sgLogs_fileNum(SG_LOGS_MAXAGE, remote_executor):
    SG_LOGS_FILES_NUM = {}
    for log in SG_LOGS_MAXAGE:
        _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
        SG_LOGS_FILES_NUM[log] = stdout[0].rstrip()

    return SG_LOGS_FILES_NUM


def send_request_to_sgw(sg_one_url, sg_admin_url, remote_executor, sg_platform="centos"):
    if sg_platform == "windows":
        command = "for ((i=1;i <= 2000;i += 1)); do curl -s {}/ABCD/ > /dev/null; done".format(sg_one_url)
        os.system(command)
        command = "for ((i=1;i <= 2000;i += 1)); do curl -s -H 'Accept: text/plain' {}/db/ > /dev/null; done".format(sg_admin_url)
        os.system(command)

    else:
        remote_executor.execute(
            "for ((i=1;i <= 2000;i += 1)); do curl -s http://localhost:4984/ABCD/ > /dev/null; done")
        remote_executor.execute(
            "for ((i=1;i <= 2000;i += 1)); do curl -s -H 'Accept: text/plain' http://localhost:4985/db/ > /dev/null; done")
