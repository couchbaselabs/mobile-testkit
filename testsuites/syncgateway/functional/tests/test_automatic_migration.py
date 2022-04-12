import pytest
import os
import json

from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, load_sync_gateway_config
from keywords.ClusterKeywords import ClusterKeywords
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from keywords import couchbaseserver
from keywords.remoteexecutor import RemoteExecutor
from keywords.constants import ENVIRONMENT_FILE
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.copy_files_to_nodes import create_files_with_content
from keywords.SyncGateway import verify_sync_gateway_version, setup_sgreplicate1_on_sgconfig
from utilities.cluster_config_utils import get_sg_version, load_cluster_config_json, is_centralized_persistent_config_disabled
from keywords.utils import log_info


@pytest.fixture(scope="function")
def sgw_version_reset(request, params_from_base_test_setup):
    sg_conf_name = "sync_gateway_default"
    sync_gateway_previous_version = params_from_base_test_setup['sync_gateway_previous_version']
    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_obj = SyncGateway()
    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, sg_conf)
    yield {
        "cluster_conf": cluster_conf,
        "sg_obj": sg_obj,
        "mode": mode,
        "sg_conf_name": sg_conf_name,
        "sync_gateway_previous_version": sync_gateway_previous_version,
        "cbs_cluster": cbs_cluster
    }
    sg_latest_version = get_sg_version(cluster_conf)
    try:
        verify_sync_gateway_version(sg1.ip, sg_latest_version)
    except Exception as ex:
        sg_obj.install_sync_gateway(cluster_conf, sg_latest_version, sg_conf, skip_bucketcreation=True)


@pytest.fixture(scope="function")
def server_restart(sgw_version_reset):
    cluster_conf = sgw_version_reset["cluster_conf"]
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    coucbase_servers = topology["couchbase_servers"]
    cbs_url = coucbase_servers[0]
    server = couchbaseserver.CouchbaseServer(cbs_url)
    yield {
        "server": server
    }
    server.start()


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
    4. Upgrade SGW to lithium and verify new version of SGW config
    5. Verify all the above configs converted to new format.
        Default config for dynamic config like logging should have default values on _config rest end point
    6. verify backup file
    """

    sg_conf_name = sgw_version_reset['sg_conf_name']
    cluster_conf = sgw_version_reset['cluster_conf']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    mode = params_from_base_test_setup['mode']
    cbs_cluster = sgw_version_reset['cluster_conf']
    sg_platform = params_from_base_test_setup["sg_platform"]
    sync_gateway_previous_version = sgw_version_reset['sync_gateway_previous_version']

    # 1. Have prelithium config
    # 2. Have configs required for database on prelithium config
    if sync_gateway_version < "3.0.0" and not is_centralized_persistent_config_disabled(cluster_conf):
        pytest.skip('This test can run with sgw version 3.0 and with persistent config off')
    # 1. Have 3 SGW nodes: 1 node as pre-lithium and 2 nodes on lithium

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 3. Add dynamic config like log_file_path or redaction_level on sgw config
    cbs_cluster = Cluster(config=cluster_conf)
    sg_obj = SyncGateway()

    # 4. Upgrade SGW to lithium  and verify new version of SGW config
    sg_obj.upgrade_sync_gateways(cluster_config=cluster_conf, sg_conf=sg_conf, sgw_previous_version=sync_gateway_previous_version, sync_gateway_version=sync_gateway_version)

    # 5. Verify all the above configs converted to new format.
    #   Default config for dynamic config like logging should have default values on _config rest end point
    sg1 = cbs_cluster.sync_gateways[0]
    cbs_url = cbs_cluster.servers[0].host
    debug_dict = {"enabled": True, "rotation": {}}
    sg1_config = sg1.admin.get_config()
    assert cbs_url in sg1_config["bootstrap"]["server"], "server did not match with legacy config"
    assert sg1_config["bootstrap"]["username"] == "data-bucket", "username did not match with legacy config"

    assert not sg1_config["logging"]["console"]["rotation"], "logging did not get reset"
    assert not sg1_config["logging"]["error"]["rotation"], "logging did not get reset"
    assert not sg1_config["logging"]["warn"]["rotation"], "logging did not get reset"
    assert not sg1_config["logging"]["info"]["rotation"], "logging did not get reset"
    assert sg1_config["logging"]["debug"] == debug_dict, "logging did not get reset"
    assert not sg1_config["logging"]["trace"]["rotation"], "logging did not get reset"
    assert not sg1_config["logging"]["stats"]["rotation"], "logging did not get reset"
    # 6. verify backup file
    if sg_platform == "windows" or "macos" in sg_platform:
        json_cluster = load_cluster_config_json(cluster_conf)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(sg1.ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(sg1.ip)
    if "macos" in sg_platform:
        sg_home_directory = "/Users/sync_gateway"
    elif sg_platform == "windows":
        sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
    else:
        sg_home_directory = "/home/sync_gateway"
    command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
    if sg_platform == "windows":
        command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
    _, stdout, _ = remote_executor.execute(command)
    assert stdout[0].strip() == str(1), "back up file did not get created"


@pytest.mark.syncgateway
@pytest.mark.parametrize("persistent_config", [
    (False),
    (True)
])
def test_automatic1_upgrade_with_replication_config(params_from_base_test_setup, persistent_config):
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
    sync_gateway_previous_version = params_from_base_test_setup['sync_gateway_previous_version']
    mode = params_from_base_test_setup['mode']
    sg_obj = SyncGateway()
    sg_conf_name = 'sync_gateway_sg_replicate1_in_sgwconfig'

    username = "autotest"
    password = "password"
    sg_channels = ["cpc"]
    remote_url = "http://10.100.10.100"
    remote_db = "remote_db"

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    temp_sg_config_copy, _ = copy_sgconf_to_temp(sg_config, mode)
    if sync_gateway_previous_version < "2.8.0":
        replication_1, _ = setup_sgreplicate1_on_sgconfig(remote_url, remote_db, username, password, channels=sg_channels, continuous=True)
    else:
        replication_1, _ = setup_replications_on_sgconfig(remote_url, remote_db, username, password, channels=sg_channels, continuous=True)
    replications_ids = "{}".format(replication_1)
    replications_key = "replications"
    if sync_gateway_previous_version < "2.8.0":
        replace_string = "\"{}\": {}{}{},".format(replications_key, "[", replications_ids, "]")
        temp_sg_config_with_sg1 = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sgreplicate2_replications }}", "")
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config_with_sg1, "{{ replace_with_sg1_replications }}", "")
    else:
        replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replications_ids, "}")
        temp_sg_config_with_sg1 = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sg1_replications }}", "")
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config_with_sg1, "{{ replace_with_sgreplicate2_replications }}", replace_string)

    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    cbs_url = topology['couchbase_servers'][0]

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    if persistent_config:
        persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', False)
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, temp_sg_config, cluster_conf)

    # 4. Verify replication are migrated and stored in bucket
    sg_dbs = sg1.admin.get_dbs()
    cbs_bucket = cbs_cluster.servers[0].get_bucket_names()[0]
    sg1_config = sg1.admin.get_config()
    assert cbs_url.split(":")[1] in sg1_config["bootstrap"]["server"], "server did not match with legacy config"
    assert sg1_config["bootstrap"]["username"] == cbs_bucket, "username did not match with legacy config"

    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_dbs[0])
    if sync_gateway_previous_version < "2.8.0":
        assert len(active_tasks) == 0, "sg replicate1 migrated and showing as replicate2 tasks"
    else:
        assert len(active_tasks) == 1, "replication tasks did not migrated successfully"


@pytest.mark.syncgateway
def test_automatic_migration_with_server_connection_fails(params_from_base_test_setup, sgw_version_reset, server_restart):
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

    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    mode = sgw_version_reset['mode']
    cluster_conf = sgw_version_reset["cluster_conf"]
    sg_conf_name = sgw_version_reset["sg_conf_name"]
    sg_obj = sgw_version_reset['sg_obj']
    server = server_restart['server']

    sg_platform = params_from_base_test_setup['sg_platform']

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 2. Have SGW config with replication config on
    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]

    # 3. stop the serve
    server.stop()
    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    try:
        sg_obj.upgrade_sync_gateways(cluster_config=cluster_conf, sg_conf=sg_conf, sgw_previous_version=sync_gateway_version, sync_gateway_version=sync_gateway_version)
    except Exception as ex:
        if "Could not upgrade sync_gateway" in str(ex):
            log_info("SGW failed to start after upgrade as server is down")

        # 4. Verify replication are migrated and stored in bucket
        # 5. Have SGW failed to start with server reconnection failure
        # 6. Verify backup file is not created and sgw config is not upgraded and old config is not intacted
        remote_executor = RemoteExecutor(sg1.ip, sg_platform)
        if "macos" in sg_platform:
            sg_home_directory = "/Users/sync_gateway"
        elif sg_platform == "windows":
            sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
        else:
            sg_home_directory = "/home/sync_gateway"
        command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
        if sg_platform == "windows":
            command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
        _, stdout, _ = remote_executor.execute(command)
        assert stdout[0].strip() == str(0), "back file did not get created"
        command = "grep bootstrap {}/sync_gateway.json| wc -l".format(sg_home_directory)
        if sg_platform == "windows":
            command = "grep bootstrap {}/sync_gateway.json| wc -l".format(sg_home_directory)
        _, stdout, _ = remote_executor.execute(command)
        assert stdout[0].strip() == str(0), "sync gateway config did not get migrated"


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
@pytest.mark.parametrize("nonWritable_directory_permissions", [
    (False),
    (True)
])
@pytest.mark.syncgateway
def test_automatic_migration_fails_with_directory_permissions(params_from_base_test_setup, sgw_version_reset, setup_env_variables, nonWritable_directory_permissions):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    ""1.Have prelithium config
    2. Once SGW is connected successfully to the server
    3. Deploy the sgw config on the directory which sync gateway user does not have permissions
    4. upgrade to 3.0 and above
    5. Verify SGW stats successfully
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
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    sg1 = cbs_cluster.sync_gateways[0]

    # 3. Deploy the sgw config on the directory which sync gateway user does not have permissions
    if sg_platform == "windows":
        sgw_config_dir = "C:\\\\tmp\\\\sgw_directory"
        sgw_config_path = sgw_config_dir + "\\\\sync_gateway.json"
        environment_string = """[String[]] $v = @("CONFIG=""" + sgw_config_path + """"\")
        Set-ItemProperty HKLM:SYSTEM\CurrentControlSet\Services\SyncGateway -Name Environment -Value $v
        """
    elif "macos" in sg_platform:
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
    remote_executor.execute("rm -rf {}".format(sgw_config_dir))
    remote_executor.execute("mkdir -p {}".format(sgw_config_dir))

    data = load_sync_gateway_config(sg_conf, topology["couchbase_servers"][0], cluster_conf)
    create_files_with_content(json.dumps(data), sg_platform, sg_hostname, "sync_gateway.json", cluster_conf, path=sgw_config_path)
    if nonWritable_directory_permissions:
        remote_executor.execute("sudo chmod 555 -R {}".format(sgw_config_dir))
    else:
        remote_executor.execute("sudo chmod 777 -R -v {}".format(sgw_config_dir))
        remote_executor.execute("sudo chmod 777 -R {}/".format(sgw_config_dir))

    # 4. upgrade to 3.0 and above
    # 5. Verify SGW stats successfully
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf, cluster_conf)

    # 6. Verify backup file is not created and sgw config is not migrated to 3.0 and old config is not intacted
    remote_executor = RemoteExecutor(sg1.ip, sg_platform)
    if "macos" in sg_platform:
        sg_home_directory = sgw_config_dir
    elif sg_platform == "windows":
        sg_home_directory = sgw_config_dir
    else:
        sg_home_directory = sgw_config_dir
    command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
    if sg_platform == "windows":
        command = "ls {} | grep {} | wc -l".format(sg_home_directory, "sync_gateway-backup-")
    _, stdout, _ = remote_executor.execute(command)
    if nonWritable_directory_permissions:
        assert stdout[0].strip() == str(0), "back file is created though directory does not have permissions"
    else:
        assert stdout[0].strip() == str(1), "back file did not get created though SGW had permission to the folder"
    command = "grep bootstrap {}/sync_gateway.json| wc -l".format(sg_home_directory)
    if sg_platform == "windows":
        command = "grep bootstrap {}/sync_gateway.json| wc -l".format(sg_home_directory)
    _, stdout, _ = remote_executor.execute(command)
    if nonWritable_directory_permissions:
        assert stdout[0].strip() == str(0), "sync gateway config got migrated though SGW user does not have permissions to the directory"
    else:
        assert stdout[0].strip() == str(1), "sync gateway config did not migrated to bootstrap though SGW user has permissions to the directory"
