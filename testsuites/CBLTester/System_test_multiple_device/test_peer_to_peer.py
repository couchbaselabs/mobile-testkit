import pytest
import time
import random

from concurrent.futures import ThreadPoolExecutor
from keywords.utils import log_info
from keywords import attachment
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType", [
    (10, True, "push_pull", False, "URLEndPoint"),
    (100, True, "push_pull", True, "MessageEndPoint"),
    (10, True, "push_pull", False, "MessageEndPoint"),
    (100, False, "push", False, "URLEndPoint"),
])
def test_peer_to_peer_1to1_valid_values(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType):
    """
        @summary:
        1. Create docs on client.
        2. Start the server.
        3. Start replication from client.
        4. Verify replication is completed.
        5. Verify all docs got replicated on server
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    replicator.wait_until_replicator_idle(repl)
    # time.sleep(60)
    # print "replication is done  ....."
    # time.sleep(20)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, endPointType", [
    (10, True, "MessageEndPoint"),
    (10, False, "URLEndPoint"),
    (100, False, "MessageEndPoint"),
    (100, True, "URLEndPoint"),
])
def test_peer_to_peer2_1to1_pull_replication(params_from_base_test_setup, server_setup, num_of_docs, continuous, endPointType):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from client to pull docs.
        4. Verify replication completed.
        5. Verify all docs got replicated on client.
    """
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_server, channels=channel)

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type="pull", endPointType=endPointType)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert client_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in client "
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "MessageEndPoint"),
    (10, True, "push_pull", "URLEndPoint"),
    (100, True, "push", "MessageEndPoint"),
    (100, False, "push", "URLEndPoint")
])
def test_peer_to_peer_concurrent_replication(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from client to pull docs.
        4. Verify replication completed.
        5. Verify all docs got replicated on client.
    """

    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    client_param = "client"
    server_param = "server"

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
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
    cbl_db_docs_client = db_obj_client.getDocuments(cbl_db_client, cbl_doc_ids)

    cbl_doc_ids = db_obj_server.getDocIds(cbl_db_server)
    cbl_db_docs_server = db_obj_server.getDocuments(cbl_db_server, cbl_doc_ids)

    for doc in cbl_db_docs_client:
        if replicator_type == "push":
            assert cbl_db_docs_client[doc][client_param] == 3, "latest update did not updated on client"
        else:
            try:
                assert cbl_db_docs_client[doc][server_param] == 3, "latest update did not updated on client"
            except KeyError:
                assert cbl_db_docs_client[doc][client_param] == 3, "latest update did not updated on client"

            try:
                assert cbl_db_docs_server[doc][server_param] == 3, "latest update did not updated on server"
            except KeyError:
                assert cbl_db_docs_server[doc][client_param] == 3, "latest update did not updated on server"

    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "URLEndPoint"),
    (10, False, "push_pull", "MessageEndPoint"),
    (100, False, "push", "URLEndPoint"),
    (100, True, "push", "MessageEndPoint"),
])
def test_peer_to_peer_oneClient_toManyServers(params_from_base_test_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on client.
        2. Start the server1 and server2
        3. Start replication from client.
        4. Verify replication is completed on both servers
        5. Verify all docs got replicated on both servers
    """
    base_url_list = params_from_base_test_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
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
    repl1 = peerToPeer_client.client_start(host=server1_host, server_db_name=db_name_server1, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    repl2 = peerToPeer_client.client_start(host=server2_host, server_db_name=db_name_server2, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)

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
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "MessageEndPoint"),
    (10, False, "push_pull", "URLEndPoint"),
    (100, False, "pull", "MessageEndPoint"),
    (100, True, "pull", "URLEndPoint"),
])
def test_peer_to_peer_oneServer_toManyClients(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on server.
        2. Start the server.
        3. Start replication from clients.
        4. Verify docs got replicated on clients from server
    """
    base_url_list = params_from_base_test_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_client2 = base_url_list[2]
    base_url_client1 = base_url_list[1]
    client_replicator1 = Replication(base_url_client1)
    client_replicator2 = Replication(base_url_client2)

    peerToPeer_client1 = PeerToPeer(base_url_client1)
    peerToPeer_client2 = PeerToPeer(base_url_client2)

    cbl_db_server = cbl_db_list[0]
    cbl_db_client1 = cbl_db_list[1]
    cbl_db_client2 = cbl_db_list[2]
    db_obj_server = db_obj_list[0]
    db_obj_client1 = db_obj_list[1]
    db_obj_client2 = db_obj_list[2]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_server, channels=channel)

    # Now set up client
    repl1 = peerToPeer_client1.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client1, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    repl2 = peerToPeer_client2.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client2, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)

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


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, replicator_type, endPointType", [
    (10, "push_pull", "MessageEndPoint"),
    (100, "push", "MessageEndPoint"),
    (10, "push_pull", "URLEndPoint"),
    (100, "push", "URLEndPoint")
])
def test_peer_to_peer_filter_docs_ids(params_from_base_test_setup, server_setup, num_of_docs, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on client.
        2. Start the server.
        3. Start replication from client with doc ids list with one shot and push_pull/push
        4. Verify replication is completed.
        5. Verify docs which are filtered got replicated on server
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channel = ["peerToPeer"]

    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    # Now set up client
    num_of_filtered_ids = 5
    cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    list_of_filtered_ids = random.sample(cbl_doc_ids, num_of_filtered_ids)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type=replicator_type, documentIDs=list_of_filtered_ids, endPointType=endPointType)
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


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, replicator_type, endPointType", [
    (10, "push_pull", "MessageEndPoint"),
    (10, "push_pull", "URLEndPoint"),
    (100, "push", "MessageEndPoint"),
    (100, "push", "URLEndPoint")
])
def test_peer_to_peer_delete_docs(params_from_base_test_setup, server_setup, num_of_docs, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on client
        2. Start the server.
        3. Start replication with continuous true from client
        4. Now delete doc on client
        5. verify docs got deleted on server
    """
    base_url_list = params_from_base_test_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channel = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    doc_obj_client = Document(base_url_client)
    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=True, replication_type=replicator_type, endPointType=endPointType)
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


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "MessageEndPoint"),
    (10, False, "push_pull", "URLEndPoint"),
    (100, True, "push", "MessageEndPoint"),
    (100, True, "push", "URLEndPoint"),
])
def test_peer_to_peer_with_server_down(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
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
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    replicatorTcpListener = server_setup["replicatorTcpListener"]
    peerToPeer_server = server_setup["peerToPeer_server"]
    channel = ["peerToPeer"]

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
    client_param = "client"

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    # Bring down server when replication happens
    with ThreadPoolExecutor(max_workers=4) as tpe:
        wait_until_replicator_completes = tpe.submit(
            client_start_replicate,
            peerToPeer_client, db_obj_client, client_param, server_host,
            db_name_server, cbl_db_client, continuous, replicator_type, endPointType
        )
        restart_server = tpe.submit(
            restart_passive_peer,
            peerToPeer_server,
            replicatorTcpListener,
            cbl_db_server
        )
        repl = wait_until_replicator_completes.result()
        replicatorTcpListener = restart_server.result()
    time.sleep(2)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed  when server restarted " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "

    cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl_db_docs = db_obj_client.getDocuments(cbl_db_client, cbl_doc_ids)
    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc][client_param] == 1, "latest update did not updated on client"
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "URLEndPoint"),
    (100, True, "push_pull", "MessageEndPoint")
])
def test_peer_to_peer_resetCheckPoint(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. create docs on client
        2. start the server.
        3. replicate docs to server
        4. purge docs on client
        5. replicate again
        6. Verify  purged docs on client should not get deleted on server
        7. stop replicator
        8. call resetcheck point  api
        9. restart the replication
        10. Verify all purged docs should not exist in client, but should exist in server

    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channel = ["peerToPeer"]

    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    doc_obj = Document(base_url_client)

    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)

    # Now set up client and replicate docs to server
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    replicator.wait_until_replicator_idle(repl)

    # purge docs on client
    client_cbl_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    for i in client_cbl_doc_ids:
        doc = db_obj_client.getDocument(cbl_db_client, doc_id=i)
        mutable_doc = doc_obj.toMutable(doc)
        db_obj_client.purge(cbl_db_client, mutable_doc)
    assert db_obj_client.getCount(cbl_db_client) == 0, "Docs that got purged in client did not get deleted"
    replicator.wait_until_replicator_idle(repl)

    # Verify  purged docs on client should also get deleted on server
    assert db_obj_client.getCount(cbl_db_client) == 0, "Docs that got purged in client did not get purged on server"
    assert db_obj_server.getCount(cbl_db_server) == num_of_docs, "docs got purged in server after purging on client"
    replicator.stop(repl)

    # call reset api and restart client request and replication
    replicator.resetCheckPoint(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    assert db_obj_client.getCount(cbl_db_client) == num_of_docs, "Docs that got purged in client did not got it back from server after resetcheckpoint api"
    assert db_obj_server.getCount(cbl_db_server) == num_of_docs, "docs got purged in server after resetcheckpoint"
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "URLEndPoint"),
    (10, True, "push_pull", "MessageEndPoint"),
    (100, True, "push", "URLEndPoint"),
    (100, True, "push", "MessageEndPoint")
])
def test_peer_to_peer_replication_with_multiple_dbs(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create 3 dbs in client.
        2. Create 3 dbs in server.
        3. Create docs in all 3 dbs in client.
        3. start the server.
        4. replicate all docs of all 3 dbs of client to all 3 dbs of server
        5. Verify each db got docs from each db of client.

    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_list = server_setup["cbl_db_list"]
    peerToPeer_server = server_setup["peerToPeer_server"]
    channel = ["peerToPeer"]

    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    cbl_db_server = cbl_db_list[0]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    # Create 2 more dbs on client and servers
    cbl_dbs_client = []
    cbl_dbs_server = []
    db_names_server = []
    cbl_dbs_client.append(cbl_db_client)
    cbl_dbs_server.append(cbl_db_server)
    db_names_server.append(db_name_server)
    db_config_client = db_obj_client.configure()
    db_name2_client = "cbl_db2_client{}".format(time.time() * 1000)
    cbl_db2_client = db_obj_client.create(db_name2_client, db_config_client)
    cbl_dbs_client.append(cbl_db2_client)
    db_name3_client = "cbl_db3_client{}".format(time.time() * 1000)
    cbl_db3_client = db_obj_client.create(db_name3_client, db_config_client)
    cbl_dbs_client.append(cbl_db3_client)
    db_config_server = db_obj_server.configure()
    db_name2_server = "cbl_db2_server{}".format(time.time() * 1000)
    cbl_db2_server = db_obj_server.create(db_name2_server, db_config_server)
    db_names_server.append(db_name2_server)
    cbl_dbs_server.append(cbl_db2_server)
    db_name3_server = "cbl_db3_server{}".format(time.time() * 1000)
    cbl_db3_server = db_obj_server.create(db_name3_server, db_config_server)
    db_names_server.append(db_name3_server)
    cbl_dbs_server.append(cbl_db3_server)
    ports = [5000, 6000, 7000]

    server_host = host_list[0]

    # Start server for remaining 2 more dbs of server with differrent ports
    replicatorTcpListener2 = peerToPeer_server.server_start(cbl_db2_server, 6000)
    replicatorTcpListener3 = peerToPeer_server.server_start(cbl_db3_server, 7000)

    # Create docs in all 3 dbs in client.
    for i in xrange(3):
        db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer{}".format(i), db=cbl_dbs_client[i], channels=channel)
        print "client num of docs are {} ".format(i), db_obj_client.getCount(cbl_dbs_client[i])

    # replicate all docs of all 3 dbs of client to all 3 dbs of server
    repls = []
    for i in xrange(3):
        repl = peerToPeer_client.client_start(host=server_host, port=ports[i], server_db_name=db_names_server[i], client_database=cbl_dbs_client[i], continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
        repls.append(repl)

    for i in xrange(3):
        replicator.wait_until_replicator_idle(repls[i])

    # Verify each db got docs from each db of client.
    for i in xrange(3):
        client_cbl_doc_ids = db_obj_client.getDocIds(cbl_dbs_client[i])
        server_cbl_doc_ids = db_obj_server.getDocIds(cbl_dbs_server[i])
        for id in client_cbl_doc_ids:
            assert id in server_cbl_doc_ids, "client docs did not replicate to server for db {}".format(i)
    for i in xrange(3):
        replicator.stop(repls[i])
    peerToPeer_server.server_stop(replicatorTcpListener2)
    peerToPeer_server.server_stop(replicatorTcpListener3)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "MessageEndPoint"),
    (10, True, "push_pull", "URLEndPoint"),
    (100, False, "push", "MessageEndPoint"),
    (100, False, "push", "URLEndPoint")
])
def test_peer_to_peer_replication_with_databaseEncryption(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. create docs on client which has database encryption.
        2. start the server
        3. start replication
        4. Verify replcation happens successfully with database encryption
    """
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    base_url_list = server_setup["base_url_list"]
    replicatorTcpListener = server_setup["replicatorTcpListener"]
    peerToPeer_server = server_setup["peerToPeer_server"]
    channel = ["peerToPeer"]
    password = "encryption"

    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    peerToPeer_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    db_obj_client = db_obj_list[1]

    # set up database encryption on both server and client
    db_config = db_obj_client.configure()
    cbl_db_name1 = "cbl_db_client" + str(time.time())
    cbl_db = db_obj_client.create(cbl_db_name1, db_config)
    db_obj_client.changeEncryptionKey(cbl_db, password)
    db_obj_client.close(cbl_db)
    db_config1 = db_obj_client.configure(password=password)
    cbl_db_client2 = db_obj_client.create(cbl_db_name1, db_config1)

    db_config_server = db_obj_server.configure()
    cbl_db_name2 = "cbl_db_server" + str(time.time())
    cbl_db2 = db_obj_server.create(cbl_db_name2, db_config_server)
    db_obj_server.changeEncryptionKey(cbl_db2, password)
    db_obj_server.close(cbl_db2)
    db_config2 = db_obj_server.configure(password=password)
    cbl_db_client2_server = db_obj_server.create(cbl_db_name2, db_config2)

    # ReStart server with new server encrypted server database
    peerToPeer_server.server_stop(replicatorTcpListener)
    replicatorTcpListener1 = peerToPeer_server.server_start(cbl_db_client2_server, port=5001)
    server_host = host_list[0]
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client2, channels=channel)

    # Now set up client and replicate docs to server
    repl = peerToPeer_client.client_start(host=server_host, port=5001, server_db_name=cbl_db_name2, client_database=cbl_db_client2, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    replicator.wait_until_replicator_idle(repl)

    # Verify replication happened on server
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_client2_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peerToPeer_server.server_stop(replicatorTcpListener1)


@pytest.fixture(scope="function")
def server_setup(params_from_base_test_setup):
    base_url_list = params_from_base_test_setup["base_url_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    base_url_server = base_url_list[0]
    peerToPeer_server = PeerToPeer(base_url_server)
    cbl_db_server = cbl_db_list[0]
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")
    yield{
        "replicatorTcpListener": replicatorTcpListener,
        "peerToPeer_server": peerToPeer_server,
        "base_url_list": base_url_list,
        "base_url_server": base_url_server,
        "cbl_db_server": cbl_db_server,
        "cbl_db_list": cbl_db_list
    }
    peerToPeer_server.server_stop(replicatorTcpListener)


@pytest.mark.listener
@pytest.mark.parametrize("delete_source, attachments, number_of_updates, endPointType", [
    ('cbl1', True, 1, "MessageEndPoint"),
    ('cbl2', True, 1, "URLEndPoint"),
    ('cbl2', False, 1, "MessageEndPoint"),
    ('cbl2', False, 5, "URLEndPoint"),
])
def test_default_conflict_scenario_delete_wins(params_from_base_test_setup, server_setup, delete_source, attachments, number_of_updates, endPointType):
    """
        @summary:
        1. Create docs in cbl 1.
        2. Replicate docs to cbl 2 with push_pull and continous False
        3. Wait until replication is done and stop replication
        4. update doc in cbl 2 and delete doc in cbl 1/ delete doc in cbl 2 and update doc in cbl 1
        5. Verify delete wins
    """
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    base_url_list = params_from_base_test_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channels = ["replication-channel"]
    num_of_docs = 10

    base_url_client = base_url_list[1]
    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    # Create bulk doc json
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    server_host = host_list[0]

    # Now set up client
    replicator = Replication(base_url_client)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    server_doc_ids = server_docs.keys()

    if delete_source == 'cbl2':
        with ThreadPoolExecutor(max_workers=4) as tpe:
            cbl1_updateDocs_task = tpe.submit(
                db_obj_server.update_bulk_docs, database=cbl_db_server,
                number_of_updates=number_of_updates, doc_ids=server_doc_ids
            )
            cbl2_delete_task = tpe.submit(
                db_obj_client.delete_bulk_docs, database=cbl_db_client
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

    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)

    assert len(cbl2_docs) == 0, "did not delete docs after delete operation"
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)
    assert len(cbl2_docs) == 0, "did not delete docs after delete operation"
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    assert len(server_docs) == 0, "did not delete docs in sg after delete operation in CBL"

    # create docs with deleted docs id and verify replication happens without any issues.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    assert len(cbl2_docs) == num_of_docs
    assert len(server_docs) == len(cbl2_docs), "new doc created with same doc id as deleted docs are not created and replicated"


@pytest.mark.listener
@pytest.mark.parametrize("highrev_source, attachments, endPointType", [
    ('cbl1', True, "MessageEndPoint"),
    ('cbl1', False, "MessageEndPoint")
])
def test_default_conflict_scenario_highRevGeneration_wins(params_from_base_test_setup, server_setup, highrev_source, attachments, endPointType):

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
        11. As CBL1 revision id is higher, docs from cbl1 should get updated
    """
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    base_url_list = server_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    channels = ["replication-channel"]
    num_of_docs = 10

    base_url_client = base_url_list[1]
    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_server = cbl_db_list[0]
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    # Create bulk doc json
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_2_png_10_10)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    server_host = host_list[0]
    # Start and stop continuous replication
    replicator = Replication(base_url_client)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    server_docs = db_obj_server.getBulkDocs(cbl_db_server)
    server_doc_ids = server_docs.keys()

    if highrev_source == 'cbl2':
        db_obj_server.update_bulk_docs(database=cbl_db_server, number_of_updates=1, doc_ids=server_doc_ids)

        db_obj_client.update_bulk_docs(cbl_db_client, number_of_updates=2)

    if highrev_source == 'cbl1':
        db_obj_server.update_bulk_docs(database=cbl_db_server, number_of_updates=2, doc_ids=server_doc_ids)
        db_obj_client.update_bulk_docs(cbl_db_client)

    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)

    server_docs = db_obj_server.getBulkDocs(cbl_db_server)

    for doc in cbl2_docs:
            assert cbl2_docs[doc]["updates-cbl"] == 2, "cbl2 with high rev id is not updated "
    if highrev_source == 'cbl1':
        for sdoc in server_docs:
            assert server_docs[sdoc]["updates-cbl"] == 2, "cbl1 with high rev id is not updated"

    db_obj_server.update_bulk_docs(database=cbl_db_server, number_of_updates=3, doc_ids=server_doc_ids)
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=False, replication_type="push_pull", endPointType=endPointType)  # , authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    cbl2_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)
    verify_updates = 5
    for doc in cbl2_docs:
        count = 0
        while count < 30 and cbl2_docs[doc]["updates-cbl"] != verify_updates:
            time.sleep(1)
            cbl2_docs = db_obj_client.getDocuments(cbl_db_client, cbl2_doc_ids)
            count += 1

        assert cbl2_docs[doc]["updates-cbl"] == verify_updates, "cbl2 with high rev id is not updated "
    server_docs = db_obj_server.getBulkDocs(cbl_db_server)

    for sdoc in server_docs:
        assert server_docs[sdoc]["updates-cbl"] == verify_updates, "cb1 with high rev id is not updated"


def client_start_replicate(peerToPeer_client, db_obj_client, param, server_host, db_name_server, cbl_db_client,
                           continuous, replicator_type, endPointType):
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                          continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
    updata_bulk_docs_custom(db_obj_client, database=cbl_db_client, number_of_updates=1, param=param)
    return repl


def restart_passive_peer(peerToPeer_server, replicatorTcpListener, cbl_db_server):
    peerToPeer_server.server_stop(replicatorTcpListener)
    replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server)
    return replicatorTcpListener


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
