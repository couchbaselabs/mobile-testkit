import os
import shutil
import time
import pytest
import uuid

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

EXPECTED_IN_LOGS = True
NOT_EXPECTED_IN_THE_LOGS = False

sg_db = "db"
username = 'audit-logging-user'
password = 'password'
is_audit_logging_set = False
channels = ["audit_logging"]
auth = None
random_suffix = str(uuid.uuid4())[:8]


@pytest.fixture
def audit_logging_fixture(params_from_base_test_setup):
    # get/set the parameters
    global username
    global password
    global sg_db
    global is_audit_logging_set
    global channels
    global auth

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


def test_default_audit_settings(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    This test checks a selected number of events and checks that they are logged.
    The events values cannot be changed
    1. Trigger the tested events
    2. Check that the events are are recorded/not recorded in the audit_log file
    '''
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture
    event_user = "user" + random_suffix
    event_role = "role" + random_suffix
    tested_ids = {"53281": EXPECTED_IN_LOGS,  # public API User authetication failed
                  "53280": EXPECTED_IN_LOGS,  # public API User authetication
                  "54100": EXPECTED_IN_LOGS,  # Create user
                  "54101": EXPECTED_IN_LOGS,  # Read user
                  "54102": EXPECTED_IN_LOGS,  # Update user
                  "54103": EXPECTED_IN_LOGS,  # Delete user
                  "54110": EXPECTED_IN_LOGS,  # Create role
                  "54111": EXPECTED_IN_LOGS,  # Read role
                  "54112": EXPECTED_IN_LOGS  # Update role
                  }

    # 1. Trigger the tested events
    trigger_event_53281(sg_client=sg_client, sg_url=sg_url)
    trigger_event_53280(sg_client=sg_client, sg_url=sg_url, auth=(username, password))
    trigger_event_54100(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_event_54101(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_event_54102(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_event_54103(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_event_54110(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)
    trigger_event_54111(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)
    trigger_event_54112(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)

    # 2. Check that the events are are recorded/not recorded in the audit_log file
    audit_log_folder = get_audit_log_folder(cluster_config)
    for id in tested_ids.keys():
        pattern = ["\"id\":" + id]
        if tested_ids[id] is EXPECTED_IN_LOGS:  # we are expecting the id in the log
            print("*** Expecting event " + str(id) + " to be in the logs")
            scan_for_pattern(audit_log_folder + "/sg_audit.log", pattern)
        else:  # we are NOT expecting the id in the log
            with pytest.raises(Exception):
                print("*** Checking if event id " + str(id) + " is in the audit log - not expecting it")
                scan_for_pattern(audit_log_folder + "/sg_audit.log", pattern)


def test_audit_log_rotation(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    1. Triggering event 53280 multiple times to increaes the audit log size to more than 1MB
    2. Looking at the content of the logs directory and expecting it to contain an archive
    '''
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster = Cluster(config=cluster_config)
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # 1. Triggering event 53280 multiple times to increaes the audit log size to more than 1MB
    for i in range(0, 6500):
        trigger_event_53280(sg_client=sg_client, sg_url=sg_url, auth=(username, password))
    # 2. Looking at the content of the logs directory and expecting it to contain an archive
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


def trigger_event_53281(sg_client, sg_url):
    try:
        sg_client.get_all_docs(url=sg_url, db=sg_db, auth=("fake_user", "fake_password"))
    except (Exception):
        pass


def trigger_event_53280(sg_client, sg_url, auth):
    sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth)


def trigger_event_54100(sg_client, sg_admin_url, user):
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=user, password=password, channels=channels, auth=auth)


def trigger_event_54101(sg_client, sg_admin_url, user):
    sg_client.get_user(url=sg_admin_url, db=sg_db, name=user, auth=auth)


def trigger_event_54102(sg_client, sg_admin_url, user):
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=user, password="password1", auth=auth)


def trigger_event_54103(sg_client, sg_admin_url, user):
    sg_client.delete_user(url=sg_admin_url, db=sg_db, name=user, auth=auth)


def trigger_event_54110(sg_client, sg_admin_url, role):
    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role)


def trigger_event_54111(sg_client, sg_admin_url, role):
    sg_client.get_role(url=sg_admin_url, db=sg_db, name=role)


def trigger_event_54112(sg_client, sg_admin_url, role):
    sg_client.update_role(url=sg_admin_url, db=sg_db, name=role)


def trigger_event_53282(sg_client, sg_admin_url):
    sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
