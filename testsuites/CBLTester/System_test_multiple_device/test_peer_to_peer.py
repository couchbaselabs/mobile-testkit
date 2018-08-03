import pytest
import time
import random

from concurrent.futures import ThreadPoolExecutor
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords import document, attachment
from CBLClient.Database import Database
from CBLClient.Document import Document
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
    (100, False, "push"),
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
    
    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_server, channels=channel)
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    log_info("server started .....")

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type="pull")
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert client_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in client "
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    (100, True, "push"),
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
    client_param = "client"
    server_param = "server"

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

    # Now update the docs on both client and server
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_client_task = tpe.submit(updata_bulk_docs_custom, db_obj_client, database=cbl_db_client, number_of_updates=3, param=client_param)
        update_server_task = tpe.submit(updata_bulk_docs_custom, db_obj_server, database=cbl_db_server, number_of_updates=3, param=server_param)
        update_client_task.result()
        update_server_task.result()

    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl_db_docs = db_obj_client.getDocuments(cbl_db_client, cbl_doc_ids)
    for doc in cbl_doc_ids:
        print "cbl doc of client is ", cbl_db_docs[doc]

        if replicator_type == "push":
            assert cbl_db_docs[doc][client_param] == 3, "latest update did not updated on client"
        else:
            assert cbl_db_docs[doc][server_param] == 3, "latest update did not updated on client"

    cbl_doc_ids = db_obj_server.getDocIds(cbl_db_server)
    cbl_db_docs = db_obj_server.getDocuments(cbl_db_server, cbl_doc_ids)
    for doc in cbl_doc_ids:
        print "cbl doc of server is ", cbl_db_docs[doc]
        assert cbl_db_docs[doc][server_param] == 3, "latest update did not updated on client"
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)


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

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, replicator_type", [
    (10, "push_pull"),
    (100, "push")
])
def test_peer_to_peer_filter_docs_ids(params_from_base_suite_setup, num_of_docs, replicator_type):
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
    mode = params_from_base_suite_setup["mode"]
    username = "autotest"
    password = "password"
    channel = ["peerToPeer"]

    if mode == "di":
        pytest.skip('Filter doc ids does not work with di modes')


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
    num_of_filtered_ids = 5
    cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    list_of_filtered_ids = random.sample(cbl_doc_ids, num_of_filtered_ids)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type=replicator_type, documentIDs=list_of_filtered_ids)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_filtered_ids, "Number of docs is not equivalent to number of docs in server "
    server_cbl_doc_ids = db_obj_server.getDocIds(cbl_db_server)
    for id in list_of_filtered_ids:
        assert id in server_cbl_doc_ids
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, replicator_type", [
    (10, "push_pull"),
    # (100, "push")
])
def test_peer_to_peer_delete_docs(params_from_base_suite_setup, num_of_docs, replicator_type):
    """
        @summary:
        1. Create docs on client
        2. Start the server.
        3. Start replication with continuous true from client
        4. Now delete doc on client
        5. verify docs got deleted on server
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
    doc_obj_client = Document(base_url_client)

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=True, replication_type=replicator_type)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    
    # Now delete doc on client
    client_cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    random_cbl_id = random.choice(client_cbl_doc_ids)
    random_cbl_doc = db_obj_client.getDocument(cbl_db_client, doc_id=random_cbl_id)
    mutable_doc = doc_obj_client.toMutable(random_cbl_doc)
    log_info("Deleting doc: {}".format(random_cbl_id))
    db_obj_client.delete(database=cbl_db_client, document=mutable_doc)
    replicator.wait_until_replicator_idle(repl)

    # verify doc got deleted on server
    server_cbl_doc_ids = db_obj_server.getDocIds(cbl_db_server)
    assert random_cbl_id not in server_cbl_doc_ids, "deleted doc in client did not delete on server"
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type", [
    (10, True, "push_pull"),
    # (10, False, "push_pull"),
    # (100, True, "push"),
    # (100, False, "push"),
])
def test_peer_to_peer_with_server_down(params_from_base_suite_setup, num_of_docs, continuous, replicator_type):
    """
        @summary:
        1. Create docs on client
        2. Start the server.
        3. Start replication with continuous true from client
        4. Bring down the server
        5. Makes changes on client
        6. restart server While replication is happening
        7. verify all docs got replicated on server 
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


@pytest.mark.listener
@pytest.mark.parametrize("delete_source, attachments, number_of_updates", [
    ('cbl1', True, 1),
    ('cbl2', True, 1),
    ('cbl1', False, 1),
    ('cbl2', False, 1),
    ('cbl1', False, 5),
    ('cbl2', False, 5),
])
def test_default_conflict_scenario_delete_wins(params_from_base_suite_setup, delete_source, attachments, number_of_updates):
    """
        @summary:
        1. Create docs in cbl 1.
        2. Replicate docs to cbl 2 with push_pull and continous False
        3. Wait until replication is done and stop replication
        4. update doc in cbl 2 and delete doc in cbl 1/ delete doc in cbl 2 and update doc in cbl 1
        5. Verify delete wins
    """
    sg_config = params_from_base_suite_setup["sg_config"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    db = params_from_base_suite_setup["db"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    channels = ["replication-channel"]
    num_of_docs = 10

    base_url_client = base_url_list[1]
    base_url_server = base_url_list[0]

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    # Reset cluster to clean the data
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)
    # sg_client = MobileRestClient()

    server_host = host_list[0]
    peerToPeer_server.server_start(cbl_db_server)
    log_info("server started .....")

    # Now set up client
    replicator = Replication(base_url_client)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # Start and stop continuous replication
    # replicator = Replication(base_url)
    # sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    # session, replicator_authenticator, repl = replicator.create_session_configure_replicate(baseUrl=base_url, sg_admin_url=sg_admin_url, sg_db=sg_db, username=username, password=password,
                                                                                            # channels=channels, sg_client=sg_client, cbl_db=cbl_db, sg_blip_url=sg_blip_url, replication_type="push_pull", continuous=False)
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    server_doc_ids = server_docs.keys()
    # sg_docs = sg_docs["rows"]

    if delete_source == 'cbl2':
        with ThreadPoolExecutor(max_workers=4) as tpe:
            cbl1_updateDocs_task = tpe.submit(
                db_obj_server.update_bulk_docs, database=cbl_db_server,
                number_updates=number_of_updates, doc_ids=server_doc_ids
            )
            cbl2_delete_task = tpe.submit(
                db_obj_client.delete_bulk_docs, cbl_db=cbl_db_server
            )
            cbl1_updateDocs_task.result()
            cbl2_delete_task.result()

    if delete_source == 'cbl1':
        with ThreadPoolExecutor(max_workers=4) as tpe:
            cbl1_delete_task = tpe.submit(
                db_obj_server.delete_bulk_docs, database=cbl_db_server, doc_ids=server_doc_ids
            )
            cbl2_update_task = tpe.submit(
                db_obj_client.update_bulk_docs, cbl_db_client, number_of_updates=number_of_updates
            )
            cbl1_delete_task.result()
            cbl2_update_task.result()

    # replicator.configure_and_replicate(source_db=cbl_db_client, target_url=sg_blip_url, continuous=False,
    #                                    channels=channels)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # if sg_mode == "di":
    #     replicator.configure_and_replicate(source_db=cbl_db_client, target_url=sg_blip_url, continuous=False,
    #                                        channels=channels)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)

    assert len(cbl2_docs) == 0, "did not delete docs after delete operation"
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # replicator.configure_and_replicate(source_db=cbl_db_client, target_url=sg_blip_url, continuous=False,
    #                                    channels=channels)
    # Di mode has delay for one shot replication, so need another replication only for DI mode
    # if sg_mode == "di":
    #     replicator.configure_and_replicate(source_db=cbl_db_client, target_url=sg_blip_url, continuous=False,
    #                                        channels=channels)

    cbl2_doc_ids = db.getDocIds(cbl_db_client)
    cbl2_docs = db.getDocuments(cbl_db_client, cbl2_doc_ids)
    assert len(cbl2_docs) == 0, "did not delete docs after delete operation"
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db)
    # sg_docs = sg_docs["rows"]
    assert len(server_docs) == 0, "did not delete docs in sg after delete operation in CBL"

    # create docs with deleted docs id and verify replication happens without any issues.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    # replicator.configure_and_replicate(source_db=cbl_db_client, target_url=sg_blip_url, continuous=False,
    #                                    channels=channels)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db.getDocIds(cbl_db_client)
    cbl2_docs = db.getDocuments(cbl_db_client, cbl2_doc_ids)
    # assert len(cbl_docs) == le "did not delete docs after delete operation"
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db)
    # sg_docs = sg_docs["rows"]
    assert len(cbl2_docs) == num_of_docs
    assert len(server_docs) == len(cbl2_docs), "new doc created with same doc id as deleted docs are not created and replicated"


@pytest.mark.listener
@pytest.mark.parametrize("highrev_source, attachments", [
    ('cbl1', True),
    ('cbl2', True),
    ('cbl1', False),
    ('cbl2', False),
])
def test_default_conflict_scenario_highRevGeneration_wins(params_from_base_suite_setup, highrev_source, attachments):

    """
        @summary:
        1. Create docs in CBL2.
        2. Replicate docs to CBL1 with push_pull and continous false
        3. Wait unitl replication done and stop replication.
        4. update doc 1 times in CBL1 and update doc 2 times in CBL2 and vice versa in 2nd scenario
        5. Start replication with push pull and continous False.
        6. Wait until replication done
        7. Verfiy doc with higher rev id is updated in CBL2.
        8. Now update docs in CBL1 3 times.
        9. Start replication with push pull and continous False.
        10. Wait until replication is done
        11. As CBL1 revision id is higher, docs from
    """
    sg_config = params_from_base_suite_setup["sg_config"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    base_url = params_from_base_suite_setup["base_url"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    host_list = params_from_base_suite_setup["host_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    db = params_from_base_suite_setup["db"]
    channels = ["replication-channel"]
    num_of_docs = 10

    base_url_client = base_url_list[1]
    base_url_server = base_url_list[0]

    peerToPeer_client = PeerToPeer(base_url_client)
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    # Reset cluster to clean the data
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create bulk doc json
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)
    # sg_client = MobileRestClient()

    server_host = host_list[0]
    peerToPeer_server.server_start(cbl_db_server)
    log_info("server started .....")

    # Start and stop continuous replication
    replicator = Replication(base_url)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # sg_client.create_user(sg_admin_url, sg_db, name="autotest", password="password", channels=channels)
    # session, replicator_authenticator, repl = replicator.create_session_configure_replicate(
    #     baseUrl=base_url, sg_admin_url=sg_admin_url, sg_db=sg_db, channels=channels, sg_client=sg_client, cbl_db=cbl_db, sg_blip_url=sg_blip_url, username="autotest", password="password", replication_type="push_pull", continuous=False)
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    server_doc_ids = server_docs.keys()
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    # sg_docs = sg_docs["rows"]

    if highrev_source == 'cbl2':
        db_obj_server.update_bulk_docs(database=cbl_db_server, number_updates=1, doc_ids=server_doc_ids)

        # sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1)
        db_obj_client.update_bulk_docs(cbl_db_client, number_of_updates=2)

    if highrev_source == 'cbl1':
        db_obj_server.update_bulk_docs(database=cbl_db_server, number_updates=2, doc_ids=server_doc_ids)
        # sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2)
        db_obj_client.update_bulk_docs(cbl_db_client)

    # replicator.configure_and_replicate(source_db=cbl_db, target_url=sg_blip_url, continuous=False,
    #                                    channels=channels)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # if sg_mode == "di":
    #     replicator.configure_and_replicate(source_db=cbl_db, target_url=sg_blip_url, continuous=False,
    #                                        channels=channels)
    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)

    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, include_docs=True)
    # sg_docs = sg_docs["rows"]
    # sg_docs_values = [doc['doc'] for doc in sg_docs]

    if highrev_source == 'cbl2':
        for doc in cbl2_docs:
            assert cbl2_docs[doc]["updates-cbl"] == 2, "cbl with high rev id is not updated "
    if highrev_source == 'cbl1':
        for doc in cbl2_docs:
            assert cbl2_docs[doc]["updates"] == 2, "cbl with high rev id is not updated "
        for i in xrange(len(server_docs)):
            assert server_docs[i]["updates"] == 2, "sg with high rev id is not updated"

    db_obj_server.update_bulk_docs(database=cbl_db_server, number_updates=3, doc_ids=server_doc_ids)
    # sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=3, auth=session)
    # replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url, continuous=False,
    #                                    channels=channels)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull")  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # Di mode has delay for one shot replication, so need another replication only for DI mode
    repl = None
    # if sg_mode == "di":
    #     repl = replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url, continuous=True,
    #                                               channels=channels)
    cbl2_doc_ids = db.getDocIds(cbl_db_client)
    cbl2_docs = db.getDocuments(cbl_db_client, cbl2_doc_ids)
    for doc in cbl2_docs:
        if highrev_source == 'cbl2':
            verify_updates = 4
        if highrev_source == 'cbl1':
            verify_updates = 5
        count = 0
        while count < 30 and cbl2_docs[doc]["updates"] != verify_updates:
            time.sleep(1)
            cbl2_docs = db.getDocuments(cbl_db_client, cbl2_doc_ids)
            count += 1
        assert cbl2_docs[doc]["updates"] == verify_updates, "cbl with high rev id is not updated "
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    # sg_docs = sg_docs["rows"]
    # sg_docs_values = [doc['doc'] for doc in sg_docs]
    for i in xrange(len(server_docs)):
        assert server_docs[i]["updates"] == verify_updates, "sg with high rev id is not updated"
    # if sg_mode == "di":
    #     replicator.stop(repl)


def updata_bulk_docs_custom(db_obj, database, number_of_updates=1, param="none", doc_ids=[]):
    updated_docs = {}
    if not doc_ids:
        doc_ids = db_obj.getDocIds(database)
    log_info("updating bulk docs")

    docs = db_obj.getDocuments(database, doc_ids)
    if len(docs) < 1:
        raise Exception("cbl docs are empty , cannot update docs")
    for _ in xrange(number_of_updates):
        for doc in docs:
            doc_body = docs[doc]
            if param not in doc_body:
                doc_body[param] = 0
            doc_body[param] = doc_body[param] + 1
            updated_docs[doc] = doc_body
        db_obj.updateDocuments(database, updated_docs)


