import os
import shutil
import time
import pytest
import random

from keywords.ClusterKeywords import ClusterKeywords
from keywords.remoteexecutor import RemoteExecutor
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from keywords.exceptions import CollectionError
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.scan_logs import scan_for_pattern


sg_db = "db"
username = 'audit-logging-user'
password = 'password'
is_audit_logging_set = False


@pytest.fixture
def audit_logging_fixture(params_from_base_test_setup):
    # get/set the parameters
    global username
    global password
    global sg_db
    global is_audit_logging_set

    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    cluster = Cluster(config=cluster_config)
    admin_client = Admin(cluster.sync_gateways[0])
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_client = MobileRestClient()
    channels = ["audit_logging"]
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    db_config = {"bucket": "data-bucket", "num_index_replicas": 0}
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    if sync_gateway_version < "3.2.0":
        pytest.skip('This test cannnot run with sg version below 3.2.0')
    if xattrs_enabled:
        pytest.skip('There is no need to run this test with xattrs_enabled')
    if is_audit_logging_set is False:
        cluster = Cluster(config=cluster_config)
        sg_conf = sync_gateway_config_path_for_mode("audit_logging", "cc")
        cluster.reset(sg_config_path=sg_conf, use_config=True)
        is_audit_logging_set = True
        if admin_client.does_db_exist(sg_db) is False:
            admin_client.create_db(sg_db, db_config)
        if admin_client.does_user_exist(sg_db, username) is False:
            sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    yield sg_client, admin_client, sg_url, sg_admin_url

    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)
    remote_executor.execute("rm -rf /home/sync_gateway/logs/audit_log*")


def test_configure_audit_logging(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    1. Enable audit logging by resetting the cluster
    2. Randomly configure the tested events, to be recorded or not recorded
    3. Trigger the tested events
    4. Check that the events are are recorded/not recorded in the audit_log file
    '''
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture

    # 2. Randomly configure the tested events, to be recorded or not recorded.
    tested_ids = {"53281": bool(random.randint(0, 1)), "53280": bool(random.randint(0, 1))}
    audit_config = {"enabled": True, "events": tested_ids}
    admin_client.replace_audit_config(sg_db, audit_config)

    # 3. Trigger the tested events
    # Triggering event 53281: public API User authetication failed
    try:
        sg_client.get_all_docs(url=sg_url, db=sg_db, auth=("fake_user", "fake_password"))
    except (Exception):
        pass
    # Triggering event 53280: public API User authetication
    sg_client.get_all_docs(url=sg_url, db=sg_db, auth=(username, password))
    # End of triggered events

    # 4. Check that the events are are recorded/not recorded in the audit_log file
    audit_log_folder = get_audit_log_folder(cluster_config)
    for id in tested_ids.keys():
        pattern = ["\"id\":" + id]
        if tested_ids[id] is True:  # we are expecting the id in the log
            print("*** Expecting event " + str(id) + " to be in the logs")
            scan_for_pattern(audit_log_folder + "/sg_audit.log", pattern)
        else:  # we are NOT expecting the id in the log
            with pytest.raises(Exception):
                print("*** Checking if even id " + str(id) + " is in the audit log - not expecting it")
                scan_for_pattern(audit_log_folder + "/sg_audit.log", pattern)


def test_audit_log_rotation(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    1. Enable event 53280 - public API authetication
    2. Triggering event 53280 multiple times to increaes the audit log size to more than 1MB
    3. Looking at the content of the logs directory and expecting it to contain an archive
    '''
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster = Cluster(config=cluster_config)
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # 1. Enable event 53280 - public API authetication
    audit_config = {"enabled": True, "events": {"53280": True}}
    admin_client.update_audit_config(sg_db, audit_config)

    # 2. Triggering event 53280 multiple times to increaes the audit log size to more than 1MB
    for i in range(0, 6500):
        sg_client.get_all_docs(url=sg_url, db=sg_db, auth=(username, password))
    # 3. Looking at the content of the logs directory and expecting it to contain an archive
    _, stdout, _ = remote_executor.execute("ls /home/sync_gateway/logs | grep sg_audit.*.gz")
    if len(stdout) > 0:
        assert ".log.gz" in stdout[0], "The archive for the rotation was not found even though it was expected"
    else:
        assert False, "The archive for the rotation was not found even though it was expected"


def get_audit_log_folder(cluster_config):
    ansible_runner = AnsibleRunner(cluster_config)

    log_info("Pulling sync_gateway / sg_accel logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml")
    if status != 0:
        raise CollectionError("Could not pull logs")
    temp_log_path = ""
    # zip logs and timestamp
    if os.path.isdir("/tmp/sg_logs"):
        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        temp_log_path = "/tmp/{}-{}-sglogs".format("audit-logging", date_time)
        shutil.copytree("/tmp/sg_logs", temp_log_path)
        return "{}/sg1".format(temp_log_path)
