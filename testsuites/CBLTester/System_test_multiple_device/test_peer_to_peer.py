import pytest
import time

from concurrent.futures import ThreadPoolExecutor
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords import document, attachment
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from CBLClient.PeerToPeer import PeerToPeer
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    (10, False, "push_pull"),
    (100, True, "push"),
    (100, False, "pull"),
])
def test_peer_to_peer_1to1_valid_values(params_from_base_suite_setup, num_of_docs, continuous, replicator_type):
    """
        @summary:
        1. Create docs on client.
        2. Start the server.
        3. Start replication from client.
        4. Verify replication is completed.
        5. Verify all docs got replicated on server
    """
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    num_of_docs = 10
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    username = "autotest"
    password = "password"
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)
    

    base_url_client = base_url_list[1]
    base_url_server = base_url_list[0]
    replicator = Replication(base_url_client)
    

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)



@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous", [
    (10, True),
    (10, False),
    (100, True),
    (100, False),
])
def test_peer_to_peer2_1to1_pull_replication(params_from_base_suite_setup, num_of_docs, continuous):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from client to pull docs.
        4. Verify replication completed.
        5. Verify all docs got replicated on client.
    """
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    num_of_docs = 10
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    username = "autotest"
    password = "password"
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channel)
    cookie, session = sg_client.create_session(sg_admin_url, sg_db, username)

    base_url_client = base_url_list[1]
    base_url_server = base_url_list[0]
    replicator = Replication(base_url_client)
    authenticator = Authenticator(base_url_client)
    replicator_authenticator = authenticator.authentication(session, cookie, authentication_type=authenticator_type)

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_server, channels=channel)
    peerToPeer_server.server_start(cbl_db_server)
    log_info("server started .....")

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, authenticator=replicator_authenticator, replication_type="pull")
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert client_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in client "
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    (10, False, "push_pull"),
    (100, True, "pull"),
    (100, False, "pull"),
])
def test_peer_to_peer_concurrent_replication(params_from_base_suite_setup, num_of_docs, continuous, replicator_type):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from client to pull docs.
        4. Verify replication completed.
        5. Verify all docs got replicated on client.
    """

    """"STilll working on it    ....... """
    cluster_config = params_from_base_suite_setup["cluster_config"]
    num_of_docs = 10
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)

    base_url_client = base_url_list[1]
    base_url_server = base_url_list[0]
    replicator = Replication(base_url_client)
    client_database = Database(base_url_client)
    server_database = Database(base_url_server)
    
    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")

    # Now set up client
    # repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, authenticator=replicator_authenticator, replication_type=replicator_type)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    
    # Now update the docs on both client and server
    db_obj_client.update_bulk_docs(database=cbl_db_client, num_of_updates=2)
    db_obj_server.update_bulk_docs(database=cbl_db_server, num_of_updates=2)

    replicator.wait_until_replicator_idle(repl)
    
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    # for doc in cbl_doc_ids:
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    (10, False, "push_pull"),
    (100, True, "push"),
    (100, False, "push"),
])
def test_peer_to_peer_oneClient_toManyServers(params_from_base_suite_setup, num_of_docs, continuous, replicator_type):
    """
        @summary:
        1. Create docs on client.
        2. Start the server1 and server2
        3. Start replication from client.
        4. Verify replication is completed on both servers
        5. Verify all docs got replicated on both servers
    """
    cluster_config = params_from_base_suite_setup["cluster_config"]
    num_of_docs = 10
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)

    base_url_client = base_url_list[2]
    base_url_server1 = base_url_list[0]
    base_url_server2 = base_url_list[1]
    client_replicator = Replication(base_url_client)
    
    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server1 = PeerToPeer(base_url_server1)
    peerToPeer_server2 = PeerToPeer(base_url_server2)
    cbl_db_server1 = cbl_db_list[0]
    cbl_db_server2 = cbl_db_list[1]
    db_obj_server1 = db_obj_list[0]
    db_obj_server2 = db_obj_list[1]
    cbl_db_client = cbl_db_list[2]
    db_obj_client = db_obj_list[2]
    db_name_server1 = db_name_list[0]
    db_name_server2 = db_name_list[1]

    server1_host = host_list[0]
    server2_host = host_list[1]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    replicatorTcpListener1 = peerToPeer_server1.server_start(cbl_db_server1)
    replicatorTcpListener2 = peerToPeer_server2.server_start(cbl_db_server2)
    log_info("servers starting .....")

    # Now set up client
    repl1 = peerToPeer_client.client_start(host=server1_host, server_db_name=db_name_server1, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type)
    repl2 = peerToPeer_client.client_start(host=server2_host, server_db_name=db_name_server2, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type)

    client_replicator.wait_until_replicator_idle(repl1)
    client_replicator.wait_until_replicator_idle(repl2)
    total = client_replicator.getTotal(repl1)
    completed = client_replicator.getCompleted(repl1)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count1 = db_obj_server1.getCount(cbl_db_server1)
    server_docs_count2 = db_obj_server2.getCount(cbl_db_server2)
    assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in server1 "
    assert server_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in server2 "
    client_replicator.stop(repl1)
    client_replicator.stop(repl2)
    peerToPeer_server1.server_stop(replicatorTcpListener1)
    peerToPeer_server2.server_stop(replicatorTcpListener2)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    (10, False, "push_pull"),
    (10, True, "pull"),
    (100, False, "pull"),
])
def test_peer_to_peer_oneServer_toManyClients(params_from_base_suite_setup, num_of_docs, continuous, replicator_type):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from clients.
        4. Verify docs got replicated on clients from server
    """
    cluster_config = params_from_base_suite_setup["cluster_config"]
    num_of_docs = 10
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)

    base_url_client2 = base_url_list[2]
    base_url_server = base_url_list[0]
    base_url_client1 = base_url_list[1]
    client_replicator1 = Replication(base_url_client1)
    client_replicator2 = Replication(base_url_client2)
    
    peerToPeer_client1 = PeerToPeer(base_url_client1)
    peerToPeer_client2 = PeerToPeer(base_url_client2)
    peerToPeer_server = PeerToPeer(base_url_server)
    
    cbl_db_server = cbl_db_list[0]
    cbl_db_client1 = cbl_db_list[1]
    cbl_db_client2 = cbl_db_list[2]
    db_obj_server = db_obj_list[0]
    db_obj_client1 = db_obj_list[1]
    db_obj_client2 = db_obj_list[2]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_server, channels=channel)
    replicatorTcpListener1 = peerToPeer_server.server_start(cbl_db_server)
    log_info("servers starting .....")

    # Now set up client
    repl1 = peerToPeer_client1.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client1, continuous=continuous, replication_type=replicator_type)
    repl2 = peerToPeer_client2.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client2, continuous=continuous, replication_type=replicator_type)

    client_replicator1.wait_until_replicator_idle(repl1)
    client_replicator2.wait_until_replicator_idle(repl2)
    total = client_replicator1.getTotal(repl1)
    completed = client_replicator1.getCompleted(repl1)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    client_docs_count1 = db_obj_client1.getCount(cbl_db_client1)
    client_docs_count2 = db_obj_client2.getCount(cbl_db_client2)
    assert client_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in client1 "
    assert client_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in client2 "
    client_replicator1.stop(repl1)
    client_replicator2.stop(repl2)
    peerToPeer_server.server_stop(replicatorTcpListener1)

