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
from utilities.cluster_config_utils import persist_cluster_config_environment_prop

EXPECTED_IN_LOGS = True
NOT_EXPECTED_IN_THE_LOGS = False
EVENTS = {"public_api_auth_failed": "53281",
          "public_api_auth_success": "53280",
          "create_user": "54100",
          "read_user": "54101",
          "update_user": "54102",
          "delete_user": "54103",
          "create_role": "54110",
          "read_role": "54111",
          "update_role": "54112",
          "create_document": "55000",
          "read_document": "55001",
          "update_document": "55002",
          "delete_document": "55003",
          "audit_enabled": "53248",
          "audit_configuration_changed": "53250",
          "sgw_startup": "53260",
          "public_api_request": "53270",
          "read_all_databases": "54003",
          "admin_http_api_request": "53271",
          "import document": "55005",
          "public_user_session_created": "53282",
          "public_user_delete_session": "53283",
          "admin_user_authenticated": "53290",
          "admin_api_auth_failed": "53291",
          "admin_api_auth_unauzthrized": "53292"
          }

DEFAULT_EVENTS_SETTINGS = {EVENTS["public_api_auth_failed"]: EXPECTED_IN_LOGS,
                           EVENTS["public_api_auth_success"]: EXPECTED_IN_LOGS,
                           EVENTS["create_user"]: EXPECTED_IN_LOGS,
                           EVENTS["read_user"]: EXPECTED_IN_LOGS,
                           EVENTS["update_user"]: EXPECTED_IN_LOGS,
                           EVENTS["delete_user"]: EXPECTED_IN_LOGS,
                           EVENTS["create_role"]: EXPECTED_IN_LOGS,
                           EVENTS["read_role"]: EXPECTED_IN_LOGS,
                           EVENTS["update_role"]: EXPECTED_IN_LOGS,
                           EVENTS["public_user_session_created"]: EXPECTED_IN_LOGS,
                           EVENTS["public_user_delete_session"]: EXPECTED_IN_LOGS,
                           EVENTS["admin_user_authenticated"]: EXPECTED_IN_LOGS,
                           EVENTS["admin_api_auth_failed"]: EXPECTED_IN_LOGS,
                           EVENTS["admin_api_auth_unauzthrized"]: EXPECTED_IN_LOGS,
                           EVENTS["create_document"]: NOT_EXPECTED_IN_THE_LOGS,
                           EVENTS["read_document"]: NOT_EXPECTED_IN_THE_LOGS,
                           EVENTS["update_document"]: NOT_EXPECTED_IN_THE_LOGS,
                           EVENTS["delete_document"]: NOT_EXPECTED_IN_THE_LOGS
                           }


# The global events as defined in resources/sync_gateway_configs_cpc/audit_logging_cc.json or unfirtable settings
GLOBAL_EVENTS_SETTINGS = {EVENTS["audit_enabled"]: EXPECTED_IN_LOGS,
                          EVENTS["audit_configuration_changed"]: EXPECTED_IN_LOGS,
                          EVENTS["sgw_startup"]: EXPECTED_IN_LOGS,
                          EVENTS["public_api_request"]: EXPECTED_IN_LOGS,
                          EVENTS["read_all_databases"]: NOT_EXPECTED_IN_THE_LOGS,
                          EVENTS["admin_http_api_request"]: NOT_EXPECTED_IN_THE_LOGS
                          }

random_suffix = str(uuid.uuid4())[:8]
sg_db = "db_" + random_suffix
sg2_db = "db2_" + random_suffix
username = 'audit-logging-user'
password = 'password'
is_audit_logging_set = False
channels = ["audit_logging"]
admin_auth = (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
bucket = "data-bucket"
bucket2 = "audit-logging-bucket2"
remote_executor = None
scope = "audit-scope" + random_suffix
collection = "audit-collection" + random_suffix


@pytest.fixture
def audit_logging_fixture(params_from_base_test_setup):
    # get/set the parameters
    global username
    global password
    global sg_db
    global is_audit_logging_set
    global channels
    global bucket2
    global remote_executor
    global scope
    global collection

    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    cluster = Cluster(config=cluster_config)
    admin_client = Admin(cluster.sync_gateways[0])
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_client = MobileRestClient()
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cbs_url = topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)
    sync_function = "function(doc){channel(doc.channels);}"

    # TODO: only reset the cluster to configure audit logging once, to save test time.
    # At the moment, the attempts to delete the audit log requires a SGW restart, and clearing the log
    # using cho -n > sg_audit.log or similar is causing failures, for an unknown reason
    persist_cluster_config_environment_prop(cluster_config, 'disable_admin_auth', False)
    cluster = Cluster(config=cluster_config)
    sg_conf = sync_gateway_config_path_for_mode("audit_logging", "cc")
    cluster.reset(sg_config_path=sg_conf, use_config=True)
    is_audit_logging_set = True
    # Creating buckets and SGW dbs
    if bucket in cb_server.get_bucket_names():
        cb_server.delete_bucket(bucket)
    cb_server.create_bucket(cluster_config, bucket, 100)
    cb_server.create_bucket(cluster_config, bucket2, 100)
    cb_server.create_scope(bucket2, scope)
    cb_server.create_collection(bucket2, scope, collection)
    if admin_client.does_db_exist(sg_db) is False:
        admin_client.create_db(sg_db, {"bucket": bucket, "num_index_replicas": 0})
    if admin_client.does_db_exist(sg2_db) is False:
        data = {"bucket": bucket2, "scopes": {scope: {"collections": {collection: {"sync": sync_function}}}}, "num_index_replicas": 0}
        admin_client.create_db(sg2_db, data)
    if admin_client.does_user_exist(sg_db, username) is False:
        sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=admin_auth)
    yield sg_client, admin_client, sg_url, sg_admin_url

    cb_server.delete_bucket(bucket)
    cb_server.delete_bucket(bucket2)


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
    trigger_user_auth_failed(sg_client=sg_client, sg_url=sg_url)
    trigger_user_auth_succeeded(sg_client=sg_client, sg_url=sg_url, auth=(username, password))
    trigger_create_user(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_get_user(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_update_user(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_update_delete(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_create_role(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)
    trigger_read_role(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)
    trigger_update_role(sg_client=sg_client, sg_admin_url=sg_admin_url, role=event_role)
    trigger_create_document(sg_client, sg_url, doc_id_prefix, auth=(username, password))
    trigger_read_document(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))
    trigger_update_document(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))
    trigger_delete_document(sg_client, sg_url, doc_id_prefix + "_0", auth=(username, password))
    _, session_id = trigger_create_public_user_session(sg_client, sg_admin_url)
    trigger_delete_user_session(sg_client, sg_admin_url, username, session_id)
    trigger_admin_auth_failed(sg_client, sg_admin_url)
    trigger_admin_auth_unauthorized(sg_client, sg_admin_url, auth=admin_auth)

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
        trigger_user_auth_succeeded(sg_client=sg_client, sg_url=sg_url, auth=(username, password))
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
    sg_client, _, sg_url, sg_admin_url = audit_logging_fixture
    cluster_config = params_from_base_test_setup["cluster_config"]
    db1_pattern = re.compile('\"db\":\"{}\".*\"id\":{}'.format(sg_db, EVENTS["create_role"]))
    db2_pattern = re.compile('\"db\":\"{}\".*\"id\":{}'.format(sg2_db, EVENTS["create_user"]))
    db_scopes_and_collections_pattern = re.compile('\"db\":\"{}\".*\"id\":{}'.format(sg2_db, EVENTS["create_document"]))

    # 1. Triggering 2 events in 2 different dbs
    trigger_create_role(sg_client, sg_admin_url, role="db1_role", db=sg_db)
    trigger_create_user(sg_client=sg_client, sg_admin_url=sg_admin_url, user="db2_user", db=sg2_db)
    trigger_create_document_with_scopes_collections(sg_client, sg_url, db=sg2_db, auth=("db2_user", "password"))
    # 2. Checking that the right event was logged against the right db
    audit_log_folder = get_audit_log_folder(cluster_config)
    with open(audit_log_folder + "/sg_audit.log", mode="rt", encoding="utf-8") as docFile:
        doc = docFile.read()
        is_db1_event_in_logs = re.findall(db1_pattern, doc)
        is_db2_event_in_logs = re.findall(db2_pattern, doc)
        is_db2_to_collection_create_doc_event_logged = re.findall(db_scopes_and_collections_pattern, doc)
        assert is_db1_event_in_logs, "The event for db1 was not recorded properly. The audit log file: " + str(doc)
        assert is_db2_event_in_logs, "The event for db2 was not recorded properly. The audit log file: " + str(doc)
        assert is_db2_to_collection_create_doc_event_logged, "The create document event was not recorded properly. The document was uploaded to a collection. The audit log file: " + str(doc)


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
    trigger_admin_http_api_request(sg_client=sg_client, sg_admin_url=sg_admin_url, user=event_user)
    trigger_public_api_request(sg_client, sg_url, auth=(username, password), db=sg_db)
    trigger_audit_configuration_change(admin_client, db=sg_db)
    trigger_get_all_databases(admin_client)

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


def trigger_user_auth_failed(sg_client, sg_url, db=sg_db):
    try:
        sg_client.get_all_docs(url=sg_url, db=db, auth=("fake_user", "fake_password"))
    except (Exception):
        pass


def trigger_user_auth_succeeded(sg_client, sg_url, auth, db=sg_db):
    sg_client.get_all_docs(url=sg_url, db=db, auth=auth)


def trigger_create_user(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.create_user(url=sg_admin_url, db=db, name=user, password=password, channels=channels, auth=admin_auth)


def trigger_get_user(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.get_user(url=sg_admin_url, db=db, name=user, auth=admin_auth)


def trigger_update_user(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.update_user(url=sg_admin_url, db=db, name=user, password="password1", auth=admin_auth)


def trigger_update_delete(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.delete_user(url=sg_admin_url, db=db, name=user, auth=admin_auth)


def trigger_create_role(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.create_role(url=sg_admin_url, db=db, name=role, auth=admin_auth)


def trigger_read_role(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.get_role(url=sg_admin_url, db=db, name=role, auth=admin_auth)


def trigger_update_role(sg_client, sg_admin_url, role, db=sg_db):
    sg_client.update_role(url=sg_admin_url, db=db, name=role, auth=admin_auth)


def trigger_admin_http_api_request(sg_client, sg_admin_url, user, db=sg_db):
    sg_client.create_user(url=sg_admin_url, db=db, name=user, password=password, channels=channels, auth=admin_auth)


def trigger_public_api_request(sg_client, sg_url, auth, db=sg_db):
    sg_client.get_all_docs(url=sg_url, db=db, auth=auth)


def trigger_audit_configuration_change(admin_client, db=sg_db):
    eventsConfiguration = admin_client.get_audit_logging_conf(db)
    audit_config = {"enabled": True, "events": {"53280": not eventsConfiguration["events"]["53280"]}}
    admin_client.replace_audit_config(db, audit_config)


def trigger_get_all_databases(admin_client):
    admin_client.get_dbs()


def trigger_create_document(sg_client, sg_url, doc_id_prefix, auth):
    sgdoc_bodies = document.create_docs(doc_id_prefix=doc_id_prefix, number=3, channels=channels)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=auth)


def trigger_read_document(sg_client, sg_url, doc_id, auth):
    sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)


def trigger_update_document(sg_client, sg_url, doc_id, auth):
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)


def trigger_delete_document(sg_client, sg_url, doc_id, auth):
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=auth)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=auth)


def trigger_create_document_with_scopes_collections(sg_client, sg_url, db, auth):
    sg_client.add_docs(url=sg_url, db=db, number=3, id_prefix="audit_collection_1_doc" + random_suffix, auth=auth, scope=scope, collection=collection, channels=["A"])


def trigger_create_public_user_session(sg_client, sg_admin_url):
    return sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=admin_auth)


def trigger_delete_user_session(sg_client, sg_admin_url, user, session_id):
    sg_client.delete_session(sg_admin_url, db=sg_db, user_name=user, session_id=session_id, auth=admin_auth)


def trigger_admin_auth_failed(sg_client, sg_admin_url):
    try:
        sg_client.create_user(url=sg_admin_url, db=sg_db, name="dummy_user" + random_suffix, password=password, channels=channels, auth=("fake_user", "fake_password"))
    except (Exception):
        pass


def trigger_admin_auth_unauthorized(sg_client, sg_admin_url, auth):
    try:
        sg_client.create_user(sg_admin_url, db=sg_db, user_name="dummy_user" + random_suffix, auth=auth)
    except (Exception):
        pass


# 53284	Public API user all sessions deleted	All sessions were deleted for a Public API user
# 53291	Admin API user authentication failed	Admin API user failed to authenticate
# 53292	Admin API user authorization failed	Admin API user failed to authorize
