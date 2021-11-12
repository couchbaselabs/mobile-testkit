import pytest
import time
import os
import json
import concurrent.futures

# from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, load_sync_gateway_config
# from keywords import document
# from keywords.utils import host_for_url, deep_dict_compare
# from couchbase.bucket import Bucket
# from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
""" from libraries.testkit import cluster
from concurrent.futures import ThreadPoolExecutor
from libraries.testkit.prometheus import verify_stat_on_prometheus
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config """
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
# from libraries.testkit.syncgateway import construct_dbconfig_json
# from CBLClient.Replication import Replication
# from CBLClient.Authenticator import Authenticator
from keywords import couchbaseserver
from keywords.remoteexecutor import RemoteExecutor
from keywords.constants import ENVIRONMENT_FILE
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.copy_files_to_nodes import create_files_with_content



@pytest.mark.syncgateway
@pytest.mark.attachment_cleanup
def test_automatic_migration_with_server_connection_fails(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/1RrrIcIZN7MgLDlNzGWfUHo2NTYrx1Jr55SBNeCdDUQs/edit#gid=0
    1. Once SGW is connected successfully to the server,
    2. Create a document with attachments and delete the attachments
    3. stop the server
    4. upgrade to 3.0 and above
    5. Have SGW  start with server
    6. Execute the compaction API
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']
    mode = sgw_version_reset['mode']
    sg_obj = sgw_version_reset["sg_obj"]
    cluster_conf = sgw_version_reset["cluster_conf"]
    sg_conf_name = sgw_version_reset["sg_conf_name"]

    # sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["attachments-cleanup"]
    remote_db = "remote_db"

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)

    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, sg_conf)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]

    cbs_cluster.reset(sg_config_path=temp_sg_config)

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, temp_sg_config,
                                cluster_conf)

    # 4. Verify replication are migrated and stored in bucket
    sg_dbs = sg1.admin.get_dbs_from_config()
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_dbs[0])
    assert len(active_tasks == 1, "replication tasks did not migrated successfully")


@pytest.fixture(scope="function")
def sgw_version_reset(request, params_from_base_test_setup):
    # sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sg_conf_name = "sync_gateway_default"
    sync_gateway_previous_version = params_from_base_test_setup['sync_gateway_previous_version']
    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_obj = SyncGateway()
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, sg_conf, skip_bucketcreation=True)
    yield {
        "cluster_conf": cluster_conf,
        "sg_obj": sg_obj,
        "mode": mode,
        "sg_conf_name": sg_conf_name,
        "sync_gateway_previous_version": sync_gateway_previous_version
    }
