import os
import shutil
import time
import pytest
import random

from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info, host_for_url
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from keywords.SyncGateway import sync_gateway_config_path_for_mode, get_sync_gateway_version
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from keywords.exceptions import LogScanningError, CollectionError
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.scan_logs import scan_for_pattern, unzip_log_files







def test_configure_audit_logging(params_from_base_test_setup):
    '''
    @summary:
    1. Enable audit logging by resetting the cluster
    2. Randomly configure the tested events, to be recorded or not recorded
    3. Trigger the tested events
    4. Check that the events are are recorded/not recorded in the audit_log file
    '''
    cluster_config = params_from_base_test_setup["cluster_config"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    cluster = Cluster(config=cluster_config)
    admin_client = Admin(cluster.sync_gateways[0])
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_db = "db"
    sg_client = MobileRestClient()
    username = 'audit-logging-user'
    password = 'password'
    channels = ["audit_logging"]
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    db_config = {"bucket": "data-bucket", "num_index_replicas": 0}
    # 1. Enable audit logging by resetting the cluster
    cluster = Cluster(config=cluster_config)
    sg_conf = sync_gateway_config_path_for_mode("audit_logging", "cc")
    cluster.reset(sg_config_path=sg_conf, use_config=True)
    if admin_client.does_db_exist(sg_db) is False:
        admin_client.create_db(sg_db, db_config)
    if admin_client.does_user_exist(sg_db, username) is False:
        sg_client.create_user(url=sg_admin_url, db=sg_db, name=username, password=password, channels=channels, auth=auth)

    # 2. Randomly configure the tested events, to be recorded or not recorded.
    tested_ids = {"53281": bool(random.randint(0,1)), "53280": bool(random.randint(0,1))}
    audit_config = {"enabled": True, "events": tested_ids}
    admin_client.replace_audit_config(sg_db, audit_config)

########################### 3. Trigger the tested events #########################################
    # Triggering event 53281: public API User authetication failed
    try:
        sg_client.get_all_docs(url=sg_url, db=sg_db, auth=("fake_user", "fake_password"))
    except:
        pass
    # Triggering event 53280: public API User authetication
    sg_client.get_all_docs(url=sg_url, db=sg_db, auth=(username, password))
########################### End of triggered events #########################################

    # 4. Check that the events are are recorded/not recorded in the audit_log file
    audit_log_path = get_audit_log_path(cluster_config, tested_ids)
    for id in tested_ids.keys():
        pattern =  ["\"id\":" + id]
        if tested_ids[id] is True: # we are expecting the id in the log
            print("*** Expecting event " + str(id) + " to be in the logs")
            scan_for_pattern(audit_log_path + "/sg_audit.log", pattern)
        else:
            with pytest.raises(Exception) as e:
                print("*** Checking if even id " + str(id) + " is in the audit log - not expecting it")
                scan_for_pattern(audit_log_path + "/sg_audit.log", pattern)


def get_audit_log_path(cluster_config, tested_ids):
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
