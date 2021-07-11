import pytest
import time

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, create_docs_via_sdk
from keywords import document
from keywords.utils import host_for_url, deep_dict_compare
from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit import cluster
from concurrent.futures import ThreadPoolExecutor
from libraries.testkit.prometheus import verify_stat_on_prometheus
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from libraries.testkit.syncgateway import construct_dbconfig_json
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator


@pytest.fixture(scope="function")
def sgw_version_reset(request, params_from_base_test_setup):
    # sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sg_conf_name = "sync_gateway_default"
    sync_gateway_previous_version = params_from_base_test_setup['sync_gateway_previous_version']
    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_obj = SyncGateway()
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, sg_conf)
    yield {
        "cluster_conf": cluster_conf,
        "sg_obj": sg_obj,
        "mode": mode,
        "sg_conf_name": sg_conf_name,
        "sync_gateway_previous_version": sync_gateway_previous_version
    }

@pytest.mark.syncgateway
def test_default_config_values(params_from_base_test_setup):
    """
    @summary :
    "1. Set up 2 nodes in the SGW cluster
    2. Have default value of default_persistent_config value on SGW nodes.
    3. Have min bootstrap configuration without static system config with differrent config on each node
        like data-bucket 1 for SGW node1 and data-bucket2 for SGW node 2.
    4. Verify each SGW node connect to each bucket and each one has differrnent configure
    5. Verify _config rest end point and validate that static system config had default value
    6. Now edit the SGW config to have differrent value of stattic system config on each SGW node
    7. Verify _config rest end point and validate thatstatic system config has overrided with the values mentioned in the config and had default values for dynamic system config"
    """

    sg_db = 'db'
    sg_conf_name = "sync_gateway_default"
    sg_obj = SyncGateway()
    # sg_conf_name2 = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    mode = params_from_base_test_setup['mode']
    sg_platform = params_from_base_test_setup['sg_platform']
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    username = "autotest"
    password = "password"
    sg_channels = ["non_cpc"]

    # 1. Have prelithium config
    # 2. Have configs required fo database on prelithium config
    if sync_gateway_upgraded_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')
    # 1. Have 3 SGW nodes: 1 node as pre-lithium and 2 nodes on lithium
    persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', False)
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()
    sg_obj = SyncGateway()
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    
    # cluster_utils = ClusterKeywords(cluster_conf)
    # cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    # 3. Add dynamic config like log_file_path or redaction_level on sgw config
    persist_cluster_config_environment_prop(cluster_conf, 'redactlevel', "partial",
                                            property_name_check=False)
    cbs_cluster = Cluster(config=cluster_conf)
    cbs_cluster.reset(sg_config_path=sg_conf)


@pytest.mark.syncgateway
def test_automatic_upgrade(params_from_base_test_setup, sgw_version_reset):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    "Same as above except Step # 2
    After step #2. Add dynamic Config
    Verify on _config end point that default values of dynamic config is overried on bucket . 
    ""As part of the steps
    "" 


    ""1. Have prelithium config with configs like 
        """"interface"""":"""":4984"""",
        """"adminInterface"""": """"0.0.0.0:4985"""",
        """"maxIncomingConnections"""": 0,
        """"maxFileDescriptors"""": 90000,
        """"compressResponses"""": false,
    2. Have configs required fo database on prelithium config
        """"db"""":{
                """"import_docs"""": true,
                """"enable_shared_bucket_access"""": true,


                """"num_index_replicas"""": 0,
                """"username"""": """"data-bucket"""",
                """"password"""": """"password"""",



                """"delta_sync"""": { """"enabled"""": true},
                """"server"""":""""couchbases://172.23.104.194:"""",
                """"bucket"""":""""data-bucket"""",
                """"bucket_op_timeout_ms"""": 60000
            }
    3. Add dynamic config like log_file_path or redaction_level on sgw config 
    4. Upgrade SGW to lithium 
    5. Verify all the above configs converted to new format.
        Default config for dynamic config like logging should have default values on _config rest end point
    6. verify backup file
    7. verify new version of SGW config
    """

    sg_conf_name = "sync_gateway_default"
    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']
    mode = sgw_version_reset['mode']
    sg_obj = sgw_version_reset["sg_obj"]
    cluster_conf = sgw_version_reset["cluster_conf"]
    sg_conf_name = sgw_version_reset["sg_conf_name"]

    """sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["cpc"]"""

    # 1. Have prelithium config
    # 2. Have configs required for database on prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')
    # 1. Have 3 SGW nodes: 1 node as pre-lithium and 2 nodes on lithium
    # persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', False)

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # sg_client = MobileRestClient()
    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', "partial",
                                            property_name_check=False)
    sg_obj.install_sync_gateway(temp_cluster_config, sync_gateway_previous_version, sg_conf)
    cluster_util = ClusterKeywords(temp_cluster_config)
    topology = cluster_util.get_cluster_topology(temp_cluster_config)
    sync_gateways = topology["sync_gateways"]
    
    # cluster_utils = ClusterKeywords(cluster_conf)
    # cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    # 3. Add dynamic config like log_file_path or redaction_level on sgw config
    cbs_cluster = Cluster(config=temp_cluster_config)
    cbs_cluster.reset(sg_config_path=sg_conf)

    # 4. Upgrade SGW to lithium
    # sgw_list1 = sync_gateways[:2]
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf, temp_cluster_config)

    # 5. Verify all the above configs converted to new format.
    #   Default config for dynamic config like logging should have default values on _config rest end point
    sg1 = cbs_cluster.sync_gateways[0]
    # sg_dbs = sg1.admin.get_dbs_from_config()
    sg1_config = sg1.admin.get_config()
    assert sg1_config["logging"] is None, "logging did not get reset"
    # 6. verify backup file
    # 7. verify new version of SGW config
    

@pytest.mark.syncgateway
@pytest.mark.parametrize("persistent_config", [
    (False),
    # (True)
])
def test_automatic_upgrade_with_replication_config(params_from_base_test_setup, sgw_version_reset, persistent_config):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    ""1.Have prelithium config 
    2. Have SGW config with replication config on
    3. Automatic upgrade
    4. Verify replication are migrated and stored in bucket
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']
    mode = sgw_version_reset['mode']
    sg_obj = sgw_version_reset["sg_obj"]
    cluster_conf = sgw_version_reset["cluster_conf"]
    # sg_conf_name = sgw_version_reset["sg_conf_name"]
    sg_conf_name = 'listener_tests/listener_tests_with_replications'

    #sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["cpc"]
    remote_url = "http://10.100.10.100"
    remote_db = "remote_db"

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 2. Have SGW config with replication config on
    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    replication_1, sgw_repl1 = setup_replications_on_sgconfig(remote_url, remote_db, username, password, channels=sg_channels, continuous=True)
    replications_key = "replications"
    replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replication_1, "}")
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_replications }}", replace_string)
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    
    cbs_cluster.reset(sg_config_path=temp_sg_config)
    # sg1_config = sg1.admin.get_config()

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    if persistent_config:
        persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', False)
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, temp_sg_config, cluster_conf)

    # 4. Verify replication are migrated and stored in bucket
    
    sg_dbs = sg1.admin.get_dbs_from_config()
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_dbs[0])
    assert len(active_tasks == 1, "replication tasks did not migrated successfully")


