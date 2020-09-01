import pytest

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from keywords.constants import CLUSTER_CONFIGS_DIR
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    pytest.param('listener_tests/multiple_sync_gateways', 10, marks=pytest.mark.sanity),
    ('listener_tests/multiple_sync_gateways', 100),
    ('listener_tests/multiple_sync_gateways', 1000)
])
def test_multiple_sgs_with_differrent_revs_limit(params_from_base_test_setup, setup_customized_teardown_test, sg_conf_name, num_of_docs):
    """
        @summary:
        1. Create 2 DBs in 2 SGS
        2. Create docs in 2 CBL
        2. Set up 1 SG with revs limit 30 and SG2 with revs limit 25.
        3. Do push replication to two SGS(each DB
        to each SG).
        4. Do updates on CBL for 35 times.
        5. Continue push replication to SGs
        6. Verify that revs maintained on two SGS according to revs_limit.
        7. exchange DBs of SG and do push replication.
        8. Verify that revs maintained on two SGS according to revs_limit.

    """
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    base_url2 = params_from_base_test_setup["base_url2"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    db = Database(base_url)
    db2 = Database(base_url2)
    print("DB1", base_url)
    print("DB2", base_url2)

    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    name1 = "autotest1"
    name2 = "autotest2"
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    c = cluster.Cluster(cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c.reset(sg_config_path=sg_config)
    sg1 = c.sync_gateways[0]
    sg2 = c.sync_gateways[1]

    # Setting revs_limit to sg1
    revs_limit1 = 20
    temp_cluster_config = copy_to_temp_conf(cluster_config, sg_mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit1, property_name_check=False)
    status = sg1.restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after changing the revs_limit on sg1"

    # Setting revs_limit to sg2
    revs_limit2 = 15
    temp_cluster_config = copy_to_temp_conf(cluster_config, sg_mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit2, property_name_check=False)
    status = sg2.restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after changing the revs_limit on sg2"

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_ip = sg1.ip
    sg2_ip = sg2.ip
    sg1_url = sg1.url
    sg1_admin_url = sg1.admin.admin_url
    sg2_url = sg2.url
    sg2_admin_url = sg2.admin.admin_url
    if sg_ssl:
        protocol = "wss"
    sg1_blip_url = "{}://{}:4984/{}".format(protocol, sg1_ip, sg_db1)
    sg2_blip_url = "{}://{}:4984/{}".format(protocol, sg2_ip, sg_db2)

    print(sg1_blip_url, sg2_blip_url)
    sg_client.create_user(sg1_admin_url, sg_db1, name1, password="password", channels=channels1)
    sg_client.create_user(sg2_admin_url, sg_db2, name2, password="password", channels=channels2)

    peer_to_peer_server = PeerToPeer(base_url)
    peer_to_peer_client = PeerToPeer(base_url2)

    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    server_cbl_db_name = setup_customized_teardown_test["cbl_db_name1"]
    print("cbl_db2", cbl_db2)
    print("cbl_db1", cbl_db1, server_cbl_db_name)
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    db2.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels2)

    # . conneting peer to peer server start

    url_listener = peer_to_peer_server.server_start(cbl_db1)
    url_listener_port = peer_to_peer_server.get_url_listener_port(url_listener)

    p2p_replicator = Replication(base_url2)

    p2p_repl_config = peer_to_peer_client.configure(port=url_listener_port, host="10.0.0.36", server_db_name=server_cbl_db_name,
                                       client_database=cbl_db2, continuous=True,
                                       replication_type="push", endPointType="URLEndPoint")

    peer_to_peer_client.client_start(p2p_repl_config)
    p2p_replicator.wait_until_replicator_idle(p2p_repl_config)

    # 2. Do push replication to two SGS(each DB to each SG)
    replicator = Replication(base_url)
    replicator2 = Replication(base_url2)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    session1 = cookie, session_id
    authenticator = Authenticator(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id, cookie, authentication_type="session")

    cookie, session_id = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    session2 = cookie, session_id
    authenticator2 = Authenticator(base_url2)
    replicator_authenticator2 = authenticator2.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="push")

    # repl2 = replicator2.configure_and_replicate(
    #     source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="push")

    total = p2p_replicator.getTotal(p2p_repl_config)
    completed = p2p_replicator.getCompleted(p2p_repl_config)
    assert total == completed, "replication from client to server did not completed"
    server_docs_count = db2.getCount(cbl_db2)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server"

    db.update_bulk_docs(cbl_db1, number_of_updates=35)
    db2.update_bulk_docs(cbl_db2, number_of_updates=35)

    replicator.wait_until_replicator_idle(repl1)
    # replicator2.wait_until_replicator_idle(repl2)
    replicator.stop(repl1)
    # replicator2.stop(repl2)

    # 4. Get docs from sgs and verify revs_limit is maintained
    sg_docs = sg_client.get_all_docs(url=sg1_url, db=sg_db1, auth=session1)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg1_url, sg_db1, doc_id, auth=session1)
        assert len(revs) == revs_limit1

    sg_docs = sg_client.get_all_docs(url=sg2_url, db=sg_db2, auth=session2)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg2_url, sg_db2, doc_id, auth=session2)
        assert len(revs) == revs_limit2

    p2p_replicator.stop(p2p_repl_config)
    peer_to_peer_server.server_stop(url_listener, "URLEndPoint")

    # # 4. Get docs from sgs and verify revs_limit is maintained after switching sgs
    sg_docs = sg_client.get_all_docs(url=sg1_url, db=sg_db1, auth=session1)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg1_url, sg_db1, doc_id, auth=session1)
        assert len(revs) == revs_limit1

    sg_docs = sg_client.get_all_docs(url=sg2_url, db=sg_db2, auth=session2)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg2_url, sg_db2, doc_id, auth=session2)
        assert len(revs) == revs_limit2




def create_sync_gateways(cluster_config, sg_config_path):

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config_path)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]

    return sg1, sg2
