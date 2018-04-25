import json
import os
import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway, sync_gateway_config_path_for_mode, load_sync_gateway_config
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation_new"])
def test_log_rotation_default_values(params_from_base_test_setup, sg_conf_name):
    """Test to verify default values for rotation section:
    maxsize = 100 MB
    MaxAge = 0(do not limit the number of MaxAge)
    MaxBackups = 0(do not limit the number of backups)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
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

    # SG_LOGS = ['sg_debug', 'sg_error', 'sg_info', 'sg_warn']
    SG_LOGS = ['sg_debug', 'sg_info', 'sg_warn']
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    for log in SG_LOGS:
        # Generate a log file with size ~94MB to check that backup file not created while 100MB not reached
        file_size = 94 * 1024 * 1024
        file_name = "/tmp/sg_logs/{}.log".format(log)
        log_info("Testing log rotation for {}".format(file_name))
        sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    # iterate 5th times to verify that every time we get new backup file with ~100MB
    for i in xrange(5):
        sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
        # ~1M MB will be added to the info/debug/warn log files after the requests
        remote_executor.execute(
            "for ((i=1;i <= 2000;i += 1)); do curl -s http://localhost:4984/ABCD/ > /dev/null; done")

        # Verify num of log files for every log file type
        for log in SG_LOGS:
            file_name = "/tmp/sg_logs/{}.log".format(log)
            _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep {} | wc -l".format(log))
            log_info("Checking for {} files for {}".format(i + 1, file_name))
            assert stdout[0].rstrip() == str(i + 1)

            sg_helper.stop_sync_gateways(cluster_config=cluster_conf, url=sg_one_url)

            # Generate an empty log file with size ~100MB
            file_size = int(99.9 * 1024 * 1024)
            sg_helper.create_empty_file(cluster_config=cluster_conf, url=sg_one_url, file_name=file_name, file_size=file_size)

    sg_helper.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)

    # Remove generated conf file
    os.remove(temp_conf)
