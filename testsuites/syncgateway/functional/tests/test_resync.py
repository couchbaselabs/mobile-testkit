import pytest
import os
import time
import shutil
import subprocess

from keywords.MobileRestClient import MobileRestClient
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import CollectionError
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("custom_sync/grant_access_one", False),
    ("custom_sync/grant_access_one", True)
])
def test_resync(params_from_base_test_setup, sg_conf_name, x509_cert_auth):
    """
    https://issues.couchbase.com/browse/CBSE-5686
    @summary:
            1. Write n documents to SG
            2. Take SG database offline (via REST API)
            3. Call _resync admin API endpoint
            4. Validate that log doesn't fill up with n messages
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled:
        pytest.skip("xattrs are mandatory for this test to run")

    sg_db = "db"
    num_docs = 100
    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        cluster_config = temp_cluster_config

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)
    client = MobileRestClient()

    # Add doc to SG
    client.add_docs(
        url=sg_admin_url,
        db=sg_db,
        number=num_docs,
        id_prefix="test_changes"
    )

    # Taking DB offline
    client.take_db_offline(cluster_conf=cluster_config, db=sg_db)
    status = client.db_resync(url=sg_admin_url, db=sg_db)
    assert status == 200, "re-sync failed"
    verify_rsync_error(cluster_config=cluster_config)
    client.bring_db_online(cluster_conf=cluster_config, db=sg_db)


def verify_rsync_error(cluster_config):
    ansible_runner = AnsibleRunner(cluster_config)

    log_info("Pulling sync_gateway / sg_accel logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml")
    if status != 0:
        raise CollectionError("Could not pull logs")
    temp_log_path = ""

    if os.path.isdir("/tmp/sg_logs"):
        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        temp_log_path = "/tmp/{}-{}-sglogs".format("log-resync", date_time)
        shutil.copytree("/tmp/sg_logs", temp_log_path)

    else:
        raise Exception("Log files are not copied properly")
    cmd = "find {} -name sync_gateway_error.log | xargs grep 'WARNING: Error updating doc' | wc -l".format(temp_log_path)
    error_count = int(subprocess.check_output(cmd, shell=True))
    assert error_count == 0, "There shouldn't be a error msg for re-sync"
