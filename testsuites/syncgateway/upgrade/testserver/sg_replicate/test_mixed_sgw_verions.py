import pytest

# from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway
from keywords import document
# from keywords.utils import host_for_url, deep_dict_compare
# from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
# from libraries.testkit import cluster
from keywords import attachment
# from concurrent.futures import ThreadPoolExecutor
# from libraries.testkit.prometheus import verify_stat_on_prometheus
# from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
# from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from libraries.testkit.syncgateway import construct_dbconfig_json
# from CBLClient.Replication import Replication
# from CBLClient.Authenticator import Authenticator


@pytest.mark.syncgateway
@pytest.mark.parametrize("disable_persistent_config", [
    (True),
    (False)
])
def test_combination_of_cpc_and_noncpc(params_from_base_test_setup, disable_persistent_config):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19kJQ4_g6RroaoG2YYe0X11d9pU0xam-lb-n23aPLhO4/edit#gid=0
    1. Have 4 SGW nodes
       2 node as pre-lithium and 2 nodes on lithium
    2. Have pre-lithium node with revs_limit as 20
    3. Start pre-lithium node
    4.  Set disable_persistent_config = true on lithium nodes
    5. Have sgw node2 with revs_limit as 30 via rest end point
    6. Verify _config end point that all 3 nodes of revs_limit are differrent and not shared
    7. Restart the SGW node 2(lithium node)
    8. Verify _config end point that revs_limit is assigned to default value

    """

    sg_db = 'db'
    sg_conf_name = "sync_gateway_revs_conflict_configurable"
    sg_obj = SyncGateway()
    # sg_conf_name2 = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    mode = params_from_base_test_setup['mode']
    # sg_platform = params_from_base_test_setup['sg_platform']
    # xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    username = "autotest"
    password = "password"
    sg_channels = ["non_cpc"]

    if sync_gateway_upgraded_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')
    # 1. Have 3 SGW nodes: 1 node as pre-lithium and 2 nodes on lithium
    if disable_persistent_config:
        # persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', True)
        sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    else:
        # persist_cluster_config_environment_prop(cluster_conf, 'disable_persistent_config', False)
        sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)

    sg_client = MobileRestClient()
    # cluster_utils = ClusterKeywords(cluster_conf)
    # cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    cbs_cluster = Cluster(config=cluster_conf)
    cbs_cluster.reset(sg_config_path=sg_conf)

    # 2. 2 node as pre-lithium and 2 nodes on lithium
    sg_obj = SyncGateway()
    cluster_util = ClusterKeywords(cluster_conf)
    # cbs_url = cluster_topology['couchbase_servers'][0]
    # cbs_host = host_for_url(cbs_url)
    topology = cluster_util.get_cluster_topology(cluster_conf, lb_enable=False)
    sync_gateways = topology["sync_gateways"]
    sgw_list1 = sync_gateways[2:]
    # sg_obj.install_sync_gateway(cluster_conf, sync_gateway_upgraded_version, sg_conf_cpc)
    sg_obj.upgrade_sync_gateway(sgw_list1, sync_gateway_version, sync_gateway_upgraded_version, sg_conf, cluster_conf, verify_version=False)

    sg1 = cbs_cluster.sync_gateways[0]
    sg3 = cbs_cluster.sync_gateways[2]
    sg4 = cbs_cluster.sync_gateways[3]
    sg_dbs = sg1.admin.get_dbs_from_config()

    sg1_db_config = sg1.admin.get_db_config(sg_dbs[0])
    revs_limit1 = 20
    revs_limit2 = 22
    revs_limit3 = 24
    sg1_db_config["revs_limit"] = revs_limit1
    sg1.admin.put_db_config(sg_db, sg1_db_config)
    sg3_db_config = sg1_db_config
    sg3_db_config["revs_limit"] = revs_limit2
    sg3.admin.put_db_config(sg_db, sg3_db_config)
    sg4_db_config = sg1_db_config
    sg4_db_config["revs_limit"] = revs_limit3
    sg4.admin.put_db_config(sg_db, sg4_db_config)

    sg_client.create_user(sg1.admin.admin_url, sg_dbs[0], username, password, channels=sg_channels)
    auto_user = sg_client.create_session(url=sg1.admin.admin_url, db=sg_dbs[0], name=username)
    sg_docs = document.create_docs('cpc', number=2, channels=sg_channels)
    sg_client.add_bulk_docs(url=sg1.url, db=sg_db, docs=sg_docs, auth=auto_user)
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db, auth=auto_user)
    sg_docs = sg_docs["rows"]
    sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]

    sg_client.update_docs(url=sg1.url, db=sg_db, docs=sg_docs, number_updates=50, auth=auto_user)
    sg1_return_db = sg1.admin.get_db_config(sg_dbs[0])
    sg3_return_db = sg3.admin.get_db_config(sg_dbs[0])
    sg4_return_db = sg4.admin.get_db_config(sg_dbs[0])

    assert sg1_return_db["revs_limit"] == 20, "revs limit is not assigned value to sg1"
    assert sg3_return_db["revs_limit"] == 22, "revs limit is not assigned value to sg3"
    assert sg4_return_db["revs_limit"] == 24, "revs limit is not assigned value to sg4"

    # TODO: check the revision history for all docs and verify number of updates are alligned with revs limit

    sg3.restart(config=sg_conf, cluster_config=cluster_conf)
    sg4.restart(config=sg_conf, cluster_config=cluster_conf)
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db, auth=auto_user)
    sg_docs = sg_docs["rows"][0]
    num_of_revs_history = sg_client.get_revs_num_in_history(url=sg1.admin.admin_url, db=sg_db, doc_id=sg_doc_ids[0], auth=auto_user)
    assert num_of_revs_history == 20, "revision history did not match with revs_limit assigned on sg1"
    num_of_revs_history = sg_client.get_revs_num_in_history(url=sg3.admin.admin_url, db=sg_db, doc_id=sg_doc_ids[0])
    assert num_of_revs_history == 22, "revision history did not match with revs_limit assigned on sg3"
    num_of_revs_history = sg_client.get_revs_num_in_history(url=sg4.admin.admin_url, db=sg_db, doc_id=sg_doc_ids[0])
    assert num_of_revs_history == 24, "revision history did not match with revs_limit assigned on sg4"
