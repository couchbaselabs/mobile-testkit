import json
import os

import pytest

from jinja2 import Template

from keywords import utils
from keywords.ClusterKeywords import ClusterKeywords
from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster


def load_sync_gateway_config(sync_gateway_config, mode, server_url):
    """ Loads a syncgateway configuration for modification"""
    with open(sync_gateway_config) as default_conf:
        if mode == "cc":
            data = json.load(default_conf)
        else:
            template = Template(default_conf.read())
            temp = template.render(
                couchbase_server_primary_node=server_url,
                is_index_writer="false"
            )
            data = json.loads(temp)

    log_info("Loaded sync_gateway config: {}".format(data))
    return data


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
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

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    # read sample sg_conf
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # delete rotation from sample config
    del data['logging']["default"]["rotation"]
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    log_info("TEMP_CONF: {}".format(temp_conf))

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    remote_executor.execute("mkdir -p /tmp/sg_logs")

    remote_executor.execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*")
    # generate log file  with size  ~94MB to check that backup file not created while 100MB not reached
    remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=94850000 count=1")

    remote_executor.execute("sudo chmod 777 -R /tmp/sg_logs")
    # iterate 5th times to verify that every time we get new backup file with ~100MB
    for i in xrange(5):
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
        # ~1M MB will be added to log file after requests
        remote_executor.execute(
            "for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done")

        _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l")
        # verify num of log files
        assert stdout[0].rstrip() == str(i + 1)

        sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
        # generate log file  with size  ~99MB
        remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=104850000 count=1")

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_logKeys_string(params_from_base_test_setup, sg_conf_name):
    """Negative test to verify that we are not able start SG when
    logKeys is string
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # read sample sg_conf
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set logKeys as string in config file
    data['logging']["default"]["logKeys"] = "http"
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_nondefault_logKeys_set(params_from_base_test_setup, sg_conf_name):
    """Test to verify non default logKeys with any invalid area.
    SG should work even with non existing logging area
    (positive case)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # read sample sg_conf
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # "FAKE" not valid area in logging
    data['logging']["default"]["logKeys"] = ["HTTP", "FAKE"]
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    # Start sync_gateways
    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_maxage_10_timestamp_ignored(params_from_base_test_setup, sg_conf_name):
    """Test to verify SG continues to wrile logs in the same file even when
     timestamp for the log file has been changed
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    remote_executor.execute("mkdir -p /tmp/sg_logs")
    remote_executor.execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*")
    # generate log file with almost 1MB
    remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1")
    remote_executor.execute("sudo chmod 777 -R /tmp/sg_logs")

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set maxage = 10 days
    data['logging']["default"]["rotation"]["maxage"] = 10
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    # ~1M MB will be added to log file after requests
    remote_executor.execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done")

    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
    # change timestamp for log when SG stopped( we don't change file naming)
    remote_executor.execute("sudo touch -d \"10 days ago\" /tmp/sg_logs/sg_log_rotation*")

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)

    _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l")
    # verify that new log file was not created
    assert stdout[0].rstrip() == '2'

    # Remove generated conf file
    os.remove(temp_conf)


# https://github.com/couchbase/sync_gateway/issues/2221
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_rotation_invalid_path(params_from_base_test_setup, sg_conf_name):
    """Test to check that SG is not started with invalid logFilePath.
    OS specific case. SG should check if path correct on startup
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set non existing logFilePath
    data['logging']["default"]["logFilePath"] = "/12345/1231/131231.log"
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()

    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.skip(reason="This causes paramiko to timeout intermittently. Need to revisit.")
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_200mb(params_from_base_test_setup, sg_conf_name):
    """Test to check maxsize with value 200MB( 100Mb by default)
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    remote_executor.execute("mkdir -p /tmp/sg_logs")
    remote_executor.execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*")
    remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=204850000 count=100")
    remote_executor.execute("sudo chmod 777 -R /tmp/sg_logs")

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set maxsize by default
    data['logging']["default"]["rotation"]["maxsize"] = 200
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    # ~1M MB will be added to log file after requests
    remote_executor.execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done")

    status, stdout, stderr = remote_executor.execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l")
    # backup file should be created with 200MB
    assert stdout[0].rstrip() == '2'

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_number_backups(params_from_base_test_setup, sg_conf_name):
    """Test to check general behaviour for number of backups.
     In test the following params have been used:
        "maxsize": 1,
        "maxage": 30,
        "maxbackups": 2
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    remote_executor.execute("mkdir -p /tmp/sg_logs")
    remote_executor.execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*")
    # generate log file with almost 1MB
    remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1")
    remote_executor.execute("sudo chmod 777 -R /tmp/sg_logs")

    # iterate 5 times
    for i in xrange(5):
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # ~1M MB will be added to log file after requests
        remote_executor.execute(
            "for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done")

        _, stdout, _ = remote_executor.execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l")
        # max 3 files: 2 backups + 1 log file
        assert stdout[0].rstrip() == str(min(3, i + 2))

        sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
        # generate log file with almost 1MB
        remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1")

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)


# https://github.com/couchbase/sync_gateway/issues/2222
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_rotation_negative(params_from_base_test_setup, sg_conf_name):
    """Test log rotation with negative values for:
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

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set negative values for rotation section
    data['logging']["default"]["rotation"] = {
        "maxsize": -1,
        "maxage": -30,
        "maxbackups": -2,
        "localtime": True
    }
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")


# https://github.com/couchbase/sync_gateway/issues/2225
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_maxbackups_0(params_from_base_test_setup, sg_conf_name):
    """Test with maxbackups=0 that means do not limit the number of backups
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)

    remote_executor.execute("mkdir -p /tmp/sg_logs")
    remote_executor.execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*")
    # generate log file with almost 1MB
    remote_executor.execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1")
    remote_executor.execute("sudo chmod 777 -R /tmp/sg_logs")

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # set maxbackups=0 in config file
    data['logging']["default"]["rotation"]["maxbackups"] = 0
    # create temp config file in the same folder as sg_conf
    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    # ~1M MB will be added to log file after requests
    remote_executor.execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done")

    status, stdout, stderr = remote_executor.execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l")
    assert stdout[0].rstrip() == '2'

    # Remove generated conf file
    os.remove(temp_conf)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name", ["log_rotation"])
def test_log_logLevel_invalid(params_from_base_test_setup, sg_conf_name):
    """Run SG with non existing logLevel value
    """
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_conf)
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    server_url = utils.host_for_url(cluster_hosts["couchbase_servers"][0])

    # read sample sg_conf
    data = load_sync_gateway_config(sg_conf, mode, server_url)

    # 'debugFake' invalid value for logLevel
    data['logging']["default"]["logLevel"] = "debugFake"

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    # create temp config file in the same folder as sg_conf
    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateway(cluster_config=cluster_conf, url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)
    except ProvisioningError:
        sg_helper.start_sync_gateway(cluster_config=cluster_conf, url=sg_one_url, config=sg_conf)
        # Remove generated conf file
        os.remove(temp_conf)
        return

    # Remove generated conf file
    os.remove(temp_conf)
    pytest.fail("SG shouldn't be started!!!!")
