import os
import shutil
import time
import pytest
import uuid
import re

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
from keywords import couchbaseserver, document

EXPECTED_IN_LOGS = True
NOT_EXPECTED_IN_THE_LOGS = False
DEFAULT_EVENTS_SETTINGS = {"53281": EXPECTED_IN_LOGS,  # public API User authetication failed
                           "53280": EXPECTED_IN_LOGS,  # public API User authetication
                           "54100": EXPECTED_IN_LOGS,  # Create user
                           "54101": EXPECTED_IN_LOGS,  # Read user
                           "54102": EXPECTED_IN_LOGS,  # Update user
                           "54103": EXPECTED_IN_LOGS,  # Delete user
                           "54110": EXPECTED_IN_LOGS,  # Create role
                           "54111": EXPECTED_IN_LOGS,  # Read role
                           "54112": EXPECTED_IN_LOGS,  # Update role
                           "55000": NOT_EXPECTED_IN_THE_LOGS,  # Create document
                           "55001": NOT_EXPECTED_IN_THE_LOGS,  # Read document
                           "55002": NOT_EXPECTED_IN_THE_LOGS,  # Update document
                           "55003": NOT_EXPECTED_IN_THE_LOGS,  # Delete document
                           }


# The global events as defined in resources/sync_gateway_configs_cpc/audit_logging_cc.json or unfirtable settings
GLOBAL_EVENTS_SETTINGS = {"53248": EXPECTED_IN_LOGS,  # Auditing enabled
                          "53250": EXPECTED_IN_LOGS,  # Auditing configuration changed
                          "53260": EXPECTED_IN_LOGS,  # Sync Gateway startup
                          "53270": EXPECTED_IN_LOGS,  # Public HTTP API request
                          "54003": NOT_EXPECTED_IN_THE_LOGS,  # Read all databases
                          "53271": NOT_EXPECTED_IN_THE_LOGS   # Admin HTTP API request
                          }

random_suffix = str(uuid.uuid4())[:8]
sg_db = "db" + random_suffix
sg2_db = "db2" + random_suffix
username = 'audit-logging-user'
password = 'password'
is_audit_logging_set = False
channels = ["audit_logging"]
auth = None
bucket = "data-bucket"
bucket2 = "audit-logging-bucket2"
remote_executor = None


@pytest.fixture
def audit_logging_fixture(params_from_base_test_setup):
    # get/set the parameters
    global username
    global password
    global sg_db
    global is_audit_logging_set
    global channels
    global auth
    global bucket2
    global remote_executor

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
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cbs_url = topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # TODO: only reset the cluster to configure audit logging once, to save test time.
    # At the moment, the attempts to delete the audit log requires a SGW restart, and clearing the log
    # using cho -n > sg_audit.log or similar is causing failures, for an unknown reason
    cluster = Cluster(config=cluster_config)
    sg_conf = sync_gateway_config_path_for_mode("audit_logging", "cc")
    cluster.reset(sg_config_path=sg_conf, use_config=True)
    is_audit_logging_set = True
    # Creating buckets and SGW dbs
    if bucket in cb_server.get_bucket_names():
        cb_server.delete_bucket(bucket)
    cb_server.create_bucket(cluster_config, bucket, 100)
    cb_server.create_bucket(cluster_config, bucket2, 100)
    if admin_client.does_db_exist(sg_db) is False:
        admin_client.create_db(sg_db, {"bucket": bucket, "num_index_replicas": 0})
    if admin_client.does_db_exist(sg2_db) is False:
        admin_client.create_db(sg2_db, {"bucket": bucket2, "num_index_replicas": 0})
    if admin_client.does_user_exist(sg_db, username) is False:
        sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)
    yield sg_client, admin_client, sg_url, sg_admin_url


@pytest.mark.parametrize("settings_config", [
    ("default"),
    (True),
    (False)
])
def test_audit_settings(params_from_base_test_setup, audit_logging_fixture, settings_config):
    '''
    @summary:
    This test checks a selected number of events and checks that they are logged.
    The events values cannot be changed
    1. Trigger the tested events
    2. Check that the events are are recorded/not recorded in the audit_log file
    '''
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture
    event_user = "user" + random_suffix + str(settings_config)
    event_role = "role" + random_suffix + str(settings_config)
    doc_id_prefix = "audit_logging_doc" + random_suffix
    tested_ids = DEFAULT_EVENTS_SETTINGS
    # randomise a selected filterable events in case we are not testing the default settings
    audit_config = {"enabled": True}
    if settings_config != "default":
        for event in tested_ids.keys():
            tested_ids[event] = settings_config
        audit_config["events"] = tested_ids
    admin_client.update_audit_config(sg_db, audit_config)

    print("The audit events configuration: " + str(admin_client.get_audit_logging_conf(sg_db)))
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
    trigger_event_55000(sg_client, sg_url, doc_id_prefix, auth=(username, password))
    trigger_event_55001(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))
    trigger_event_55002(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))
    trigger_event_55003(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))

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
    sg_client, _, sg_url, _ = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster = Cluster(config=cluster_config)
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # 1. Triggering event 53280 multiple times to increaes the audit log size to more than 1MB
    for i in range(0, 3000):
        trigger_event_53280(sg_client=sg_client, sg_url=sg_url, auth=(username, password))
    # 2. Looking at the content of the logs directory and expecting it to contain an archive
    _, stdout, _ = remote_executor.execute("ls /home/sync_gateway/logs | grep sg_audit.*.gz")
    if len(stdout) > 0:
        assert ".log.gz" in stdout[0], "The archive for the rotation was not found even though it was expected"
    else:
        assert False, "The archive for the rotation was not found even though it was expected"


def test_events_logs_per_db(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    1. Triggering 2 events in 2 different dbs
    2. Checking that the right event was logged against the right db
    '''
    sg_client, _, _, sg_admin_url = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    db1_pattern = re.compile('\"db\":\"{}\".*\"id\":54110'.format(sg_db))
    db2_pattern = re.compile('\"db\":\"{}\".*\"id\":54100'.format(sg2_db))

    # 1. Triggering 2 events in 2 different dbs
    trigger_event_54110(sg_client, sg_admin_url, role="db1_role", db=sg_db)
    trigger_event_54100(sg_client=sg_client, sg_admin_url=sg_admin_url, user="db2_user", db=sg2_db)

    # 2. Checking that the right event was logged against the right db
    audit_log_folder = get_audit_log_folder(cluster_config)
    with open(audit_log_folder + "/sg_audit.log", mode="rt", encoding="utf-8") as docFile:
        doc = docFile.read()
        is_db1_event_in_logs = re.findall(db1_pattern, doc)
        is_db2_event_in_logs = re.findall(db2_pattern, doc)
        assert is_db1_event_in_logs, "The event for db1 was not recorded properly. The audit log file: " + str(doc)
        assert is_db2_event_in_logs, "The event for db2 was not recorded properly. The audit log file: " + str(doc)


def test_global_events(params_from_base_test_setup, audit_logging_fixture):
    '''
    @summary:
    1. Trigging global events
    2. Check that the events are are recorded/not recorded in the audit_log file
    '''
    sg_client, admin_client, sg_url, sg_admin_url = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    event_user = "user" + random_suffix + "ge"
    tested_ids = GLOBAL_EVENTS_SETTINGS

    # 1. Trigging global events
    trigger_event_53271(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_event_53270(sg_client, sg_url, auth=(username, password), db=sg_db)
    trigger_event_53250(admin_client, db=sg_db)
    trigger_event_54003(admin_client)

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


# public API User authetication failed
def trigger_event_53281(sg_client, sg_url, db=sg_db):
    try:
        sg_client.get_all_docs(url=sg_url, db=db, auth=("fake_user", "fake_password"))
    except (Exception):
        pass


# public API User authetication
def trigger_event_53280(sg_client, sg_url, auth, db=sg_db):
    sg_client.get_all_docs(url=sg_url, db=db, auth=auth)


# Create user
def trigger_event_54100(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.create_user(url=sg_admin_url, db=db, name=user, password=password, channels=channels, auth=auth)


# Read user
def trigger_event_54101(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.get_user(url=sg_admin_url, db=db, name=user, auth=auth)


# Update user
def trigger_event_54102(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.update_user(url=sg_admin_url, db=db, name=user, password="password1", auth=auth)


# Delete user
def trigger_event_54103(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.delete_user(url=sg_admin_url, db=db, name=user, auth=auth)


# Create role
def trigger_event_54110(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.create_role(url=sg_admin_url, db=db, name=role)


# Read role
def trigger_event_54111(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.get_role(url=sg_admin_url, db=db, name=role)


# Update role
def trigger_event_54112(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.update_role(url=sg_admin_url, db=db, name=role)


# Create session
def trigger_event_53282(sg_client, sg_admin_url, db=sg_db):
    sg_client.create_session(url=sg_admin_url, db=db, name=username, auth=auth)


# Admin HTTP API request
def trigger_event_53271(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.create_user(url=sg_admin_url, db=db, name=user, password=password, channels=channels, auth=auth)


# Public HTTP API request
def trigger_event_53270(sg_client, sg_url, auth, db=sg_db):
    sg_client.get_all_docs(url=sg_url, db=db, auth=auth)


# Audit configuration changed
def trigger_event_53250(admin_client, db=sg_db):
    eventsConfiguration = admin_client.get_audit_logging_conf(db)
    audit_config = {"enabled": True, "events": {"53280": not eventsConfiguration["events"]["53280"]}}
    admin_client.replace_audit_config(db, audit_config)


# Read all databases
def trigger_event_54003(admin_client):
    admin_client.get_dbs()


# Create document
def trigger_event_55000(sg_client, sg_url, doc_id_prefix, auth):
    sgdoc_bodies = document.create_docs(doc_id_prefix=doc_id_prefix, number=3, channels=channels)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=auth)


# Read document
def trigger_event_55001(sg_client, sg_url, doc_id, auth):
    sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)


# Update document
def trigger_event_55002(sg_client, sg_url, doc_id, auth):
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)


# Delete document
def trigger_event_55003(sg_client, sg_url, doc_id, auth):
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=auth)
