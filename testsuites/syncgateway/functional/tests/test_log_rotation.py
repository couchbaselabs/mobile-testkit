import json
import os

import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.RemoteExecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster



@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_logKeys_string(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["logKeys"] = "http"

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)
    except:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)
        return
    pytest.fail("SG shouldn't be started!!!!")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_nondefault_logKeys_set(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["logKeys"] = ["HTTP", "FAKE"]

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_maxage_10_timestamp_ignored(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

    remote_executor.must_execute("mkdir -p /tmp/sg_logs", any_status=True)

    remote_executor.must_execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*", any_status=True)

    remote_executor.must_execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1",
                                 any_status=True)

    remote_executor.must_execute("sudo chmod 777 -R /tmp/sg_logs", any_status=True)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["rotation"]["maxage"] = 10

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)

    remote_executor.must_execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done",
                                 any_status=True)

    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

    remote_executor.must_execute("sudo touch -d \"10 days ago\" /tmp/sg_logs/sg_log_rotation*", any_status=True)

    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)

    _, stdout, _ = remote_executor.must_execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l",
                                                any_status=True)

    assert stdout[0].rstrip() == '2'


# https://github.com/couchbase/sync_gateway/issues/2221
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_rotation_invalid_path(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["logFilePath"] = "/12345/1231/131231.log"

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)
    except:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)
        return
    pytest.fail("SG shouldn't be started!!!!")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_100mb(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

    remote_executor.must_execute("mkdir -p /tmp/sg_logs", any_status=True)

    remote_executor.must_execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*", any_status=True)

    remote_executor.must_execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=104850000 count=100",
                                 any_status=True)

    remote_executor.must_execute("sudo chmod 777 -R /tmp/sg_logs", any_status=True)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["rotation"]["maxsize"] = 100

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)

    remote_executor.must_execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done",
                                 any_status=True)

    status, stdout, stderr = remote_executor.must_execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l",
                                                          any_status=True)
    assert stdout[0].rstrip() == '2'


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_number_backups(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

    remote_executor.must_execute("mkdir -p /tmp/sg_logs", any_status=True)

    remote_executor.must_execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*", any_status=True)

    remote_executor.must_execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1",
                                 any_status=True)

    remote_executor.must_execute("sudo chmod 777 -R /tmp/sg_logs", any_status=True)

    for i in xrange(5):
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)

        remote_executor.must_execute(
            "for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done",
            any_status=True)

        _, stdout, _ = remote_executor.must_execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l",
                                                              any_status=True)
        assert stdout[0].rstrip() == str(min(3, i + 2))

        sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

        remote_executor.must_execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1",
                                     any_status=True)

    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)


# https://github.com/couchbase/sync_gateway/issues/2222
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_rotation_negative(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["rotation"] = {
        "maxsize": -1,
        "maxage": -30,
        "maxbackups": -2,
        "localtime": True
    }

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)
    except:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)
        return
    pytest.fail("SG shouldn't be started!!!!")


# https://github.com/couchbase/sync_gateway/issues/2225
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_maxbackups_0(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)

    remote_executor.must_execute("mkdir -p /tmp/sg_logs", any_status=True)

    remote_executor.must_execute("sudo rm -rf /tmp/sg_logs/sg_log_rotation*", any_status=True)

    remote_executor.must_execute("sudo dd if=/dev/zero of=/tmp/sg_logs/sg_log_rotation.log bs=1030000 count=1",
                                 any_status=True)

    remote_executor.must_execute("sudo chmod 777 -R /tmp/sg_logs", any_status=True)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["rotation"]["maxbackups"] = 0

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)

    remote_executor.must_execute("for ((i=1;i <= 1000;i += 1)); do curl -s http://localhost:4984/ > /dev/null; done",
                                 any_status=True)

    status, stdout, stderr = remote_executor.must_execute("ls /tmp/sg_logs/ | grep sg_log_rotation | wc -l",
                                                          any_status=True)
    assert stdout[0].rstrip() == '2'


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_log_rotation"
])
def test_log_logLevel_invalid(params_from_base_test_setup, sg_conf_name):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'sync_access_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    with open(sg_conf) as defaul_conf:
        data = json.load(defaul_conf)

    data['logging']["default"]["logLevel"] = "debugFake"

    temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'

    with open(temp_conf, 'w') as fp:
        json.dump(data, fp)

    # Stop sync_gateways
    log_info(">>> Stopping sync_gateway")
    sg_helper = SyncGateway()
    cluster_helper = ClusterKeywords()
    cluster_hosts = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    sg_one_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_helper.stop_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url)
    try:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=temp_conf)
    except:
        sg_helper.start_sync_gateway(cluster_config=os.environ["CLUSTER_CONFIG"], url=sg_one_url, config=sg_conf)
        return
    pytest.fail("SG shouldn't be started!!!!")

"""