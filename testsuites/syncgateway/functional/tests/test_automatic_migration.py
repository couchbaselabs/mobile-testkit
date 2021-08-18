import pytest
import time
import os
import json
import concurrent.futures

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, load_sync_gateway_config
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
from keywords import couchbaseserver
from keywords.remoteexecutor import RemoteExecutor
from keywords.constants import ENVIRONMENT_FILE
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.copy_files_to_nodes import create_files_with_content


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
def test_automatic1_upgrade_with_replication_config(params_from_base_test_setup, sgw_version_reset, persistent_config):
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
    sg_conf_name = sgw_version_reset["sg_conf_name"]

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


@pytest.mark.syncgateway
@pytest.mark.parametrize("persistent_config", [
    (False),
    # (True)
])
def test_automatic_migration_with_server_connection_fails(params_from_base_test_setup, sgw_version_reset, persistent_config):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    ""1.Have prelithium config 
    2. Once SGW is connected successfully to the server, 
    3. stop the server
    4. upgrade to 3.0 and above
    5. Have SGW failed to start with server reconnection failure
    6. Verify backup file is not created and sgw config is not upgraded and old config is not intacted
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']
    mode = sgw_version_reset['mode']
    sg_obj = sgw_version_reset["sg_obj"]
    cluster_conf = sgw_version_reset["cluster_conf"]
    sg_conf_name = sgw_version_reset["sg_conf_name"]
    # sg_conf_name = 'listener_tests/listener_tests_with_replications'

    #sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["cpc"]
    # remote_url = "http://10.100.10.100"
    # remote_db = "remote_db"

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 2. Have SGW config with replication config on
    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    coucbase_servers = topology["couchbase_servers"]
    
    cbs_cluster.reset(sg_config_path=sg_conf)
    # sg1_config = sg1.admin.get_config()

    # 3. stop the server
    cbs_url = coucbase_servers[0]
    server = couchbaseserver.CouchbaseServer(cbs_url)
    server.stop()
    # sg_obj.stop_sync_gateways(cluster_conf)
    # sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_conf, sg_conf=sg_conf, sync_gateway_version=sync_gateway_version, enable_import=True, deploy_only=True)
    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    with concurrent.futures.ProcessPoolExecutor() as ex:
        upgrade_process = ex.submit(sg_obj.upgrade_sync_gateways, sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf, cluster_conf)
        time.sleep(120)
        server.start()
    # 4. Verify replication are migrated and stored in bucket
    
    sg_dbs = sg1.admin.get_dbs_from_config()


@pytest.fixture(scope="function")
def setup_env_variables(params_from_base_test_setup):
    cluster_config = params_from_base_test_setup["cluster_config"]
    ansible_runner = AnsibleRunner(cluster_config)
    cbs_cluster = Cluster(config=cluster_config)
    sg_hostname = cbs_cluster.sync_gateways[0].hostname
    yield{
        "cluster_config": cluster_config,
        "cbs_cluster": cbs_cluster,
        "sg_hostname": sg_hostname,
        "ansible_runner": ansible_runner
    }
    status = ansible_runner.run_ansible_playbook(
        "remove-env-variables-for-service.yml",
        subset=sg_hostname
    )
    assert status == 0, "ansible failed to remove systemd environment variables directory"


@pytest.mark.syncgateway
def test_automatic_migration_fails_with_directory_permissions(params_from_base_test_setup, sgw_version_reset, setup_env_variables):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    ""1.Have prelithium config 
    2. Once SGW is connected successfully to the server
    3. Deploy the sgw config on the directory which sync gateway user does not have permissions
    4. upgrade to 3.0 and above
    5. Have SGW failed to start 
    6. Verify backup file is not created and sgw config is not upgraded and old config is not intacted
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']
    sg_platform = params_from_base_test_setup['sg_platform']
    mode = sgw_version_reset['mode']
    sg_obj = sgw_version_reset["sg_obj"]
    cluster_conf = sgw_version_reset["cluster_conf"]
    sg_conf_name = sgw_version_reset["sg_conf_name"]
    ansible_runner = setup_env_variables["ansible_runner"]
    sg_hostname = setup_env_variables["sg_hostname"]

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 2. Have SGW config with replication config on
    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    coucbase_servers = topology["couchbase_servers"]
    cbs_cluster.reset(sg_config_path=sg_conf)
    # sg_hostname = sg1.hostname
    
    # 3. Deploy the sgw config on the directory which sync gateway user does not have permissions
    if sg_platform == "windows":
        sgw_config_dir = "C:\\\\tmp\\\\sgw_directory"
        sgw_config_path = sgw_config_dir + "\\\\sync_gateway.json"
        environment_string = """[String[]] $v = @("CONFIG=""" + sgw_config_path + """"\")
        Set-ItemProperty HKLM:SYSTEM\CurrentControlSet\Services\SyncGateway -Name Environment -Value $v
        """
    elif sg_platform == "macos":
        sgw_config_dir = "/tmp/sgw_directory"
        sgw_config_path = sgw_config_dir + "/sync_gateway.json"
        environment_string = """launchctl setenv CONFIG """ + sgw_config_path + """
        """
    else:
        sgw_config_dir = "/tmp/sgw_directory"
        sgw_config_path = sgw_config_dir + "/sync_gateway.json"
        environment_string = """[Service]
        Environment="CONFIG=""" + sgw_config_path + """"
        """

    environment_file = os.path.abspath(ENVIRONMENT_FILE)
    environmentFileWriter = open(environment_file, "w")
    environmentFileWriter.write(environment_string)
    environmentFileWriter.close()
    playbook_vars = {
        "environment_file": environment_file
    }
    ansible_runner.run_ansible_playbook(
        "setup-env-variables-for-service.yml",
        extra_vars=playbook_vars,
        subset=sg_hostname
    )
    remote_executor = RemoteExecutor(cbs_cluster.sync_gateways[0].ip)
    remote_executor.execute("mkdir -p {}".format(sgw_config_dir))
    remote_executor.execute("sudo chmod 721 -R {}".format(sgw_config_dir))
    data = load_sync_gateway_config(sg_conf, topology["couchbase_servers"][0], cluster_conf)
    create_files_with_content(json.dumps(data), sg_platform, sg_hostname, "sync_gateway.json", cluster_conf, path=sgw_config_path)
    # sg1_config = sg1.admin.get_config()

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf, cluster_conf)

    # 4. Verify replication are migrated and stored in bucket
    
    sg_dbs = sg1.admin.get_dbs_from_config()
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_dbs[0])
    assert len(active_tasks == 1, "replication tasks did not migrated successfully")
