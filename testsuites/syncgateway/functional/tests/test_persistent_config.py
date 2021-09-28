import pytest
import time
import json

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, load_sync_gateway_config
from keywords import document
# from keywords.utils import host_for_url, deep_dict_compare
# from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
# from libraries.testkit import cluster
# from concurrent.futures import ThreadPoolExecutor
# from libraries.testkit.prometheus import verify_stat_on_prometheus
# from libraries.testkit.syncgateway import start_sgbinary, get_buckets_from_sync_gateway_config
# from libraries.testkit.syncgateway import start_sgbinary
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from libraries.testkit.syncgateway import construct_dbconfig_json
# from CBLClient.Replication import Replication
# from CBLClient.Authenticator import Authenticator
from utilities.cluster_config_utils import is_centralized_persistent_config_disabled, copy_to_temp_conf
# from keywords.remoteexecutor import RemoteExecutor


@pytest.mark.syncgateway
def test_default_config_values(params_from_base_test_setup):
    """
    @summary :
    https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    Covered #30, #7
    "1. Set up sgw node in the SGW cluster
    2. Have default value of default_persistent_config value on SGW nodes.
    3. Have min bootstrap configuration without static system config with differrent config 
    4. Verify SGW node connect to each bucket and each one has differrnent configure
    5. Verify _config rest end point and validate that static system config had default value
    6. Now have bootstrap and static config and verify default values of dynamic config
    """

    # sg_db = 'db'
    sg_conf_name = "sync_gateway_default_bootstrap"
    sg_conf_name2 = "sync_gateway_default"
    sg_obj = SyncGateway()

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    # sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    mode = params_from_base_test_setup['mode']
    """ sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["non_cpc"] """

    # 1. Have prelithium config
    # 2. Have configs required fo database on prelithium config
    if sync_gateway_version < "3.0.0" and not is_centralized_persistent_config_disabled(cluster_conf):
        pytest.skip('This test can run with sgw version 3.0 and above')
    # 1. Have 3 SGW nodes: 1 node as pre-lithium and 2 nodes on lithium
    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'disable_persistent_config', False)
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
    sg_conf2 = sync_gateway_config_path_for_mode(sg_conf_name2, mode, cpc=True)

    # sg_client = MobileRestClient() 
    sg_obj = SyncGateway()
    cluster_util = ClusterKeywords(temp_cluster_config)
    topology = cluster_util.get_cluster_topology(temp_cluster_config)
    # sync_gateways = topology["sync_gateways"]
    sg_one_url = topology["sync_gateways"][0]["public"]

    # 3. Have min bootstrap configuration without static system config with differrent config
    cbs_cluster = Cluster(config=temp_cluster_config)
    cbs_cluster.reset(sg_config_path=sg_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    sg1_config = sg1.admin.get_config()
    assert sg1_config["logging"] is None, "logging did not get reset"
    # 4. Verify default values of static config
    # 4. Add dynamic config like log_file_path or redaction_level on sgw config
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', "partial",
                                            property_name_check=False)
    sg_obj.start_sync_gateways(cluster_config=temp_cluster_config, url=sg_one_url, config=sg_conf2)

    # Verify default values of dynamic config


@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    ("sync_gateway_default_invalid_bootstrap"),
    # (sync_gateway_default)
])
def test_invalid_configs(params_from_base_test_setup, sg_conf_name):
    """
    @summary :
    https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    Covered #31
    ""1. Set up SGW node with bootstrap config and add few static config under bootstrap config
    2. Add bootstrap config under static config
    3. Verify SGW fails to restart"
    """

    # sg_db = 'db'
    # sg_conf_name = "sync_gateway_default_invalid_bootstrap"
    sg_obj = SyncGateway()

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    # sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    mode = params_from_base_test_setup['mode']
    """ sg_platform = params_from_base_test_setup['sg_platform']
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    username = "autotest"
    password = "password"
    sg_channels = ["non_cpc"] """

    # 1. Have prelithium config
    # 2. Have configs required fo database on prelithium config
    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'disable_persistent_config', False)
    if sync_gateway_version < "3.0.0" and not is_centralized_persistent_config_disabled(cluster_conf):
        pytest.skip('This test can run with sgw version 3.0 and with persistent config off')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # sg_client = MobileRestClient() 
    sg_obj = SyncGateway()
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    # sync_gateways = topology["sync_gateways"]
    sg_one_url = topology["sync_gateways"][0]["public"]

    # 3. Have min bootstrap configuration without static system config with differrent config
    if sg_conf_name == "sync_gateway_default":
        sgw_config = load_sync_gateway_config(sg_conf, topology["couchbase_servers"][0], cluster_conf)
        # Create temp config file in the same folder as sg_conf
        temp_conf = "/".join(sg_conf.split('/')[:-2]) + '/temp_conf.json'
        del sgw_config["bootstrap"]
        log_info("TEMP_CONF: {}".format(temp_conf))

        with open(temp_conf, 'w') as fp:
            json.dump(sgw_config, fp, indent=4)
            print("todo")
    cbs_cluster = Cluster(config=cluster_conf)
    cbs_cluster.reset(sg_config_path=sg_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    sg1_config = sg1.admin.get_config()
    assert sg1_config["logging"] is None, "logging did not get reset"
    # 4. Verify default values of static config
    # 4. Add dynamic config like log_file_path or redaction_level on sgw config
    persist_cluster_config_environment_prop(cluster_conf, 'redactlevel', "partial",
                                            property_name_check=False)
    sg_obj.start_sync_gateways(cluster_config=cluster_conf, url=sg_one_url, config=temp_conf)


@pytest.mark.syncgateway
def test_sgw_command_line(params_from_base_test_setup):
    """
    @summary :
    https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    Covered #33
    1. Set up sgw node in the SGW cluster
    2. Have default_persistent_config value on SGW nodes.
    3. Have min bootstrap configuration
    4. Start  sgw node by passing command line params by passing server, bucket info 
    5. Verify SGW node connect to each bucket 
    5. Verify _config rest end point and validate that params passed for bootstrap, static values are matching with command line params"
    """

    # sg_db = 'db'
    sg_conf_name = "sync_gateway_default_bootstrap"

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    mode = params_from_base_test_setup['mode']
    sg_platform = params_from_base_test_setup['sg_platform']
    """ username = "autotest"
    password = "password"
    sg_channels = ["non_cpc"] """

    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    # 2. Have default_persistent_config value on SGW nodes
    persist_cluster_config_environment_prop(temp_cluster_config, 'disable_persistent_config', False)

    # 1. Set up sgw node in the SGW cluster
    if sync_gateway_version < "3.0.0" or not is_centralized_persistent_config_disabled(cluster_conf):
        pytest.skip('This test can run with sgw version 3.0 and above')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)

    # sg_client = MobileRestClient()
    sg_obj = SyncGateway()
    # cluster_util = ClusterKeywords(temp_cluster_config)
    # topology = cluster_util.get_cluster_topology(temp_cluster_config)
    # sync_gateways = topology["sync_gateways"]
    # sg_one_url = topology["sync_gateways"][0]["public"]

    # 3. Have min bootstrap configuration
    cbs_cluster = Cluster(config=temp_cluster_config)
    cbs_cluster.reset(sg_config_path=sg_conf)

    # 4.Start sgw node by passing command line params by passing server, bucket info
    sg1 = cbs_cluster.sync_gateways[0]
    print("stopping explicetely ")
    sg_obj.stop_sync_gateways(temp_cluster_config)
    sg_obj.redeploy_sync_gateway_config(temp_cluster_config, sg_conf, url=None, sync_gateway_version=sync_gateway_version, enable_import=True, deploy_only=True)
    """ adminInterface = "5985"
    interface = "5984"
    cacertpath = ""
    certpath = ""
    configServer = ""
    dbname = "" 
    defaultLogFilePath = "/tmp/sg_logs"
    disable_persistent_config = False
    keypath = ""
    log = ""
    logFilePath = ""
    profileInterface = ""
    url = ""
    std_output = start_sgbinary(sg1, sg_platform, adminInterface=adminInterface, interface=interface, defaultLogFilePath=defaultLogFilePath, disable_persistent_config=disable_persistent_config)
    """
    count = 0
    retry = 5
    errors = 1
    while count < retry and errors != 0:
        errors = cbs_cluster.verify_alive()
        time.sleep(2)
        count += 1

    sg1_config = sg1.admin.get_config()
    assert sg1_config["logging"] is None, "logging did not get reset"
    # 4. Verify default values of static config
    # 4. Add dynamic config like log_file_path or redaction_level on sgw config


@pytest.mark.syncgateway
def test_invalid_database_credentials(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    "1. Have bootstrap config on sgw config which has server, username, password of the bucket
    2. Start SGW
    3. Add database on sgw via rest end point with invalid credentials of the bucket on the response from rest apoi
    """

    sg_db = 'sg_db'
    sg_db2 = 'sg_db2'
    # sg_db3 = 'sg_db3'
    sg_conf_name = "sync_gateway_default_bootstrap"
    # sg_obj = SyncGateway()

    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sg_platform = params_from_base_test_setup['sg_platform']

    # 1. Have bootstrap config on sgw config which has server, username, password of the bucket
    # TODO: remove below 3 lines after persistent config is default to false
    temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'disable_persistent_config', False)
    cluster_conf = temp_cluster_config
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)

    sg_client = MobileRestClient()
    """ cluster_utils = ClusterKeywords(cluster_conf)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_one_url = cluster_topology["sync_gateways"][0]["public"]
    sg_two_url = cluster_topology["sync_gateways"][1]["public"] """
    sg_db2_username = "autotest"
    sg_password = "password"
    sg_channels = ["cpc_testing"]
    # sg_username2 = "autotest2"
    # sg_channels2 = ["cpc_testing2"]
    cbs_cluster = Cluster(config=cluster_conf)
    cbs_cluster.reset(sg_config_path=sg_config)
    time.sleep(15)
    sg1 = cbs_cluster.sync_gateways[0]
    sg2 = cbs_cluster.sync_gateways[1]

    # 3. Add database config on node1 with sg_db1
    # revs_limit = 20
    # persist_cluster_config_environment_prop(cluster_conf, 'revs_limit', revs_limit, property_name_check=False)
    db_config_file = "sync_gateway_default_db"
    dbconfig = construct_dbconfig_json(db_config_file, cluster_conf, sg_platform, sg_conf_name)
    print("db config", dbconfig)
    sg1.admin.create_db_with_rest(sg_db, dbconfig)

    # 6. Verify db config end point on one of the node and verify it shows all 3 db configs
    # sg1_db1_config = sg1.admin.get_db_config(sg_db1)
    """assert"""

    # 7. Create doc, doc1 on node on sg_db2.
    sg_client.create_user(sg1.admin.admin_url, sg_db2, sg_db2_username, sg_password, channels=sg_channels)
    auto_user = sg_client.create_session(url=sg1.admin.admin_url, db=sg_db2, name=sg_db2_username)
    sg_docs = document.create_docs('cpc-union', number=2, channels=sg_channels)
    sg_client.add_bulk_docs(url=sg1.url, db=sg_db2, docs=sg_docs, auth=auto_user)

    # 8. Verify all 3 nodes can access the doc1 on sg_db2
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db2, auth=auto_user)["rows"]
    assert len(sg_docs) == 2, "sg1 node could not access sg_db2 docs"

    sg_docs = sg_client.get_all_docs(url=sg2.url, db=sg_db2, auth=auto_user)["rows"]
    assert len(sg_docs) == 2, "sg2 node could not access sg_db2 docs"

    sg_docs = sg_client.get_all_docs(url=sg3.url, db=sg_db2, auth=auto_user)["rows"]
    assert len(sg_docs) == 2, "sg3 node could not access sg_db2 docs"
