import pytest

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
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
        @summary:  SG1<->CBL1<->CB2<->SG2
        1. Start 2 SGS
        2. Create docs in SG1
        3. Sg1 connected to CBL
        4. Verify docs in CB1
        5. Connect CBL1 with CBl2
        6. Verify doc in CBL2
        7. Connect CBL2 with SG2
        8. Verify docs in SG2
    """
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    base_url2 = params_from_base_test_setup["base_url2"]
    host_list = params_from_base_test_setup["liteserv_host_list"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    db = Database(base_url)
    db2 = Database(base_url2)

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
    revs_limit2 = 25
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

    # connecting peer to peer server start
    url_listener = peer_to_peer_server.server_start(cbl_db1)
    url_listener_port = peer_to_peer_server.get_url_listener_port(url_listener)

    # Creating docs in SG
    sg_added_doc_ids, cbl_added_doc_ids, session = setup_sg_cbl_docs(sg_db=sg_db1,
                                                                     base_url=base_url, db=db,
                                                                     cbl_db=cbl_db1, sg_url=sg1_url,
                                                                     sg_admin_url=sg1_admin_url,
                                                                     sg_blip_url=sg1_blip_url,
                                                                     replication_type="push-pull", channels=channels1,
                                                                     replicator_authenticator_type="basic",
                                                                     attachments_generator=False)

    cbl_doc_count = db.getCount(cbl_db1)
    sg_docs = sg_client.get_all_docs(url=sg1_admin_url, db=sg_db1)
    assert cbl_doc_count == len(sg_docs["rows"]), "Did not get expected number of cbl docs"

    p2p_replicator = Replication(base_url2)
    p2p_repl_config = peer_to_peer_client.configure(port=url_listener_port, host=host_list[0],
                                                    server_db_name=server_cbl_db_name,
                                                    client_database=cbl_db2, continuous=True,
                                                    replication_type="push-pull", endPointType="URLEndPoint")

    # start p2p replicator
    peer_to_peer_client.client_start(p2p_repl_config)
    p2p_replicator.wait_until_replicator_idle(p2p_repl_config)

    # Make sure docs are copied to both peers
    total = p2p_replicator.getTotal(p2p_repl_config)
    completed = p2p_replicator.getCompleted(p2p_repl_config)
    assert total == completed, "replication from client to server did not completed"
    server_docs_count = db2.getCount(cbl_db2)
    assert server_docs_count == cbl_doc_count, "Number of docs is not equivalent to number of docs in server"

    # 2. Do push replication to two SGS(each DB to each SG)
    replicator2 = Replication(base_url2)
    cookie, session_id = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    authenticator2 = Authenticator(base_url2)
    replicator_authenticator2 = authenticator2.authentication(session_id, cookie, authentication_type="session")

    # Start the SG2 replicator
    repl2 = replicator2.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="push-pull")

    replicator2.wait_until_replicator_idle(repl2)

    total = replicator2.getTotal(repl2)
    completed = replicator2.getCompleted(repl2)
    assert total == completed, "total is not equal to completed"
    sg2_docs = sg_client.get_all_docs(url=sg2_admin_url, db=sg_db2, include_docs=True)
    sg2_docs = sg2_docs["rows"]

    # Verify database doc counts
    cbl2_doc_count = db2.getCount(cbl_db2)
    assert len(sg2_docs) == cbl2_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
    replicator2.stop(repl2)

    # 4. Get docs from sgs and verify revs_limit is maintained
    p2p_replicator.stop(p2p_repl_config)
    peer_to_peer_server.server_stop(url_listener, "URLEndPoint")


def setup_sg_cbl_docs(sg_db, base_url, db, cbl_db, sg_url,
                      sg_admin_url, sg_blip_url, replication_type=None, document_ids=None,
                      channels=None, replicator_authenticator_type=None, headers=None,
                      cbl_id_prefix="cbl", sg_id_prefix="sg_doc",
                      num_cbl_docs=5, num_sg_docs=10, attachments_generator=None):

    sg_client = MobileRestClient()

    db.create_bulk_docs(number=num_cbl_docs, id_prefix=cbl_id_prefix, db=cbl_db, channels=channels, attachments_generator=attachments_generator)
    cbl_added_doc_ids = db.getDocIds(cbl_db)
    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    auth_session = cookie, session
    sg_added_docs = sg_client.add_docs(url=sg_url, db=sg_db, number=num_sg_docs, id_prefix=sg_id_prefix, channels=channels, auth=auth_session, attachments_generator=attachments_generator)
    sg_added_ids = [row["id"] for row in sg_added_docs]

    # Start and stop continuous replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(username="autotest", password="password", authentication_type=replicator_authenticator_type)
    log_info("Configuring replicator")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, replication_type=replication_type, continuous=False,
                                       documentIDs=document_ids, channels=channels, replicator_authenticator=replicator_authenticator, headers=headers)
    repl = replicator.create(repl_config)
    log_info("Starting replicator")
    replicator.start(repl)
    log_info("Waiting for replicator to go idle")
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    return sg_added_ids, cbl_added_doc_ids, auth_session


def create_sync_gateways(cluster_config, sg_config_path):
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config_path)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]
    return sg1, sg2
