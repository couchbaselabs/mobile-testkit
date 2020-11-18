import random
import time
import pytest

from keywords.utils import add_new_fields_to_doc, meet_supported_version
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer
from keywords.utils import log_info
from CBLClient.Query import Query
from CBLClient.Database import Database


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, replicator_type, attachments, endpoint_type", [
    (10, "push", False, "URLEndPoint"),
    (10, "pull", False, "URLEndPoint"),
    (10, "push", False, "MessageEndPoint"),
    pytest.param(10, "pull", False, "MessageEndPoint", marks=pytest.mark.sanity),
    (100, "push", True, "URLEndPoint"),
    (100, "pull", True, "URLEndPoint"),
    (100, "push", True, "MessageEndPoint"),
    (100, "pull", True, "MessageEndPoint"),
])
def test_p2p_replication_push_pull_filtering(params_from_base_test_setup, server_setup, num_of_docs,
                                             replicator_type, attachments, endpoint_type):
    """
        @summary:
        1. Create docs on client.
        2. Start the server.
        3. Start replication from client.
        4. Verify replication is completed.
        5. Verify all docs got replicated on server
    """
    version_list = params_from_base_test_setup["version_list"]
    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")

    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]

    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    p2p_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]
    server_host = host_list[0]
    peer_to_peer_server = PeerToPeer(base_url_list[0])

    if endpoint_type == "URLEndPoint":
        replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server)
        url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    # Now set up client
    repl_config = p2p_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       replication_type="push_pull", endPointType=endpoint_type)
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    total = replicator.getTotal(repl_config)
    completed = replicator.getCompleted(repl_config)
    assert total == completed, "replication from client to server did not completed " +\
                               str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl_config)

    client_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    server_doc_ids = db_obj_server.getDocIds(cbl_db_server)

    assert sorted(client_doc_ids) == sorted(server_doc_ids), "Replication failed. Server db doesn't have same docs"

    # 3. Modify docs in client so that we can do push replication.
    if replicator_type == "push":
        push_filter = True
        pull_filter = False
        client_docs = db_obj_client.getDocuments(cbl_db_client, client_doc_ids)
        for doc_id, doc_body in list(client_docs.items()):
            doc_body = add_new_fields_to_doc(doc_body)
            db_obj_client.updateDocument(database=cbl_db_client, data=doc_body, doc_id=doc_id)
    else:
        push_filter = False
        pull_filter = True
        server_docs = db_obj_server.getDocuments(cbl_db_server, server_doc_ids)
        for doc_id, doc_body in list(server_docs.items()):
            doc_body = add_new_fields_to_doc(doc_body)
            db_obj_server.updateDocument(database=cbl_db_server, data=doc_body, doc_id=doc_id)

    # 4. The replication will have filter for newly added field
    # Docs with new_field_1 value to true will only be replicated, others will be rejected by filter method
    repl_config = p2p_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       replication_type=replicator_type, endPointType=endpoint_type,
                                       push_filter=push_filter, pull_filter=pull_filter,
                                       filter_callback_func='boolean')
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    replicator.stop(repl_config)

    # 4. Verify Server has new fields added only when "new_field_1" is true
    server_docs = db_obj_server.getDocuments(cbl_db_server, server_doc_ids)
    client_docs = db_obj_client.getDocuments(cbl_db_client, client_doc_ids)

    for doc_id in server_docs:
        if replicator_type == "push":
            if client_docs[doc_id]["new_field_1"] is True:
                assert client_docs[doc_id]["new_field_1"] == server_docs[doc_id]["new_field_1"],\
                    "new_field_1 data is not matching"
                assert client_docs[doc_id]["new_field_2"] == server_docs[doc_id]["new_field_2"],\
                    "new_field_2 data is not matching"
                assert client_docs[doc_id]["new_field_3"] == server_docs[doc_id]["new_field_3"],\
                    "new_field_3 data is not matching"
            else:
                assert "new_field_1" not in server_docs[doc_id] or "new_field_2" not in server_docs[doc_id] or \
                       "new_field_3" not in server_docs[doc_id], "updated key found in doc. Push filter is not working"
        else:
            if server_docs[doc_id]["new_field_1"] is True:
                assert client_docs[doc_id]["new_field_1"] == server_docs[doc_id]["new_field_1"],\
                    "new_field_1 data is not matching"
                assert client_docs[doc_id]["new_field_2"] == server_docs[doc_id]["new_field_2"],\
                    "new_field_2 data is not matching"
                assert client_docs[doc_id]["new_field_3"] == server_docs[doc_id]["new_field_3"],\
                    "new_field_3 data is not matching"
            else:
                assert "new_field_1" not in client_docs[doc_id] or "new_field_2" not in client_docs[doc_id] or \
                       "new_field_3" not in client_docs[doc_id], "updated key found in doc. Pull filter is not working"

    if endpoint_type == "URLEndPoint":
        peer_to_peer_server.server_stop(replicator_tcp_listener, endpoint_type)


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, attachments, endpoint_type", [
    [10, False, "URLEndPoint"],
    [100, True, "URLEndPoint"],
    [10, False, "MessageEndPoint"],
    [100, True, "MessageEndPoint"],
])
def test_p2p_replication_delete(params_from_base_test_setup, server_setup, num_of_docs,
                                attachments, endpoint_type):
    """
        @summary:
        1. Create docs on client and server.
        2. Start the server and start replication from client with push and pull.
        3. Verify replication is completed.
        4. Delete few docs on both server and client and replicate them using delete filter
        5. Verify that deleted docs on server doesn't get deleted on client and vice versa because of delete filter
    """
    version_list = params_from_base_test_setup["version_list"]
    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)
    num_of_docs_to_delete = (num_of_docs * 2) // 10

    p2p_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    peer_to_peer_server = PeerToPeer(base_url_list[0])

    if endpoint_type == "URLEndPoint":
        replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server)
        url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 1. Create docs on client and server.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "client_replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
        db_obj_server.create_bulk_docs(num_of_docs, "server_replication", db=cbl_db_server, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "client_replication", db=cbl_db_client, channels=channels)
        db_obj_server.create_bulk_docs(num_of_docs, "server_replication", db=cbl_db_server, channels=channels)

    # Now set up client
    # 2. Start the server and start replication from client with push and pull.
    repl_config = p2p_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       replication_type="push_pull", endPointType=endpoint_type)
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    total = replicator.getTotal(repl_config)
    completed = replicator.getCompleted(repl_config)
    assert total == completed, "replication from client to server did not completed " + \
                               str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == 2 * num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl_config)

    client_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    server_doc_ids = db_obj_server.getDocIds(cbl_db_server)

    # 3. Verify replication is completed.
    assert sorted(client_doc_ids) == sorted(server_doc_ids), "Replication failed. Server db doesn't have same docs"

    # 4. Delete few docs on both server and client and replicate them using delete filter
    client_ids = [doc_id for doc_id in client_doc_ids if "client" in doc_id]
    server_ids = [doc_id for doc_id in client_doc_ids if "server" in doc_id]
    client_doc_ids_to_delete = random.sample(client_ids, num_of_docs_to_delete // 2)
    server_doc_ids_to_delete = random.sample(server_ids, num_of_docs_to_delete // 2)

    db_obj_server.delete_bulk_docs(database=cbl_db_server, doc_ids=server_doc_ids_to_delete)
    db_obj_client.delete_bulk_docs(database=cbl_db_client, doc_ids=client_doc_ids_to_delete)

    repl_config = p2p_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       push_filter=True, pull_filter=True, filter_callback_func='deleted',
                                       replication_type='push_pull', endPointType=endpoint_type)
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    replicator.stop(repl_config)

    client_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    server_doc_ids = db_obj_server.getDocIds(cbl_db_server)

    # 5. Verify that deleted docs on server doesn't get deleted on client and vice versa because of delete filter
    for doc_id in client_doc_ids:
        if doc_id in client_doc_ids_to_delete:
            assert doc_id in server_doc_ids

    for doc_id in server_doc_ids:
        if doc_id in server_doc_ids_to_delete:
            assert doc_id in client_doc_ids
    if endpoint_type == "URLEndPoint":
        peer_to_peer_server.server_stop(replicator_tcp_listener, endpoint_type)


@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, attachments, endpoint_type", [
    [10, False, "URLEndPoint"],
    [100, True, "URLEndPoint"],
    [10, False, "MessageEndPoint"],
    [100, True, "MessageEndPoint"],
])
def test_p2p_filter_retrieval_with_replication_restart(params_from_base_test_setup, server_setup, num_of_docs,
                                                       attachments, endpoint_type):
    """
        @summary:
        1. Create docs on client and server.
        2. Start the server and start replication from client with push and pull with boolean filter. Nothing will be
        filtered as docs doesn't contain "new_field_1"
        3. Verify replication is completed.
        4. Add new fields to docs and restart the replication with the same configuration.
        5. Verify that docs with "new_field_1" to true only got replicated to other side.
    """
    version_list = params_from_base_test_setup["version_list"]
    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)

    p2p_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    server_host = host_list[0]
    peer_to_peer_server = PeerToPeer(base_url_list[0])

    if endpoint_type == "URLEndPoint":
        replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server)
        url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)
    else:
        url_listener_port = 5000

    # 1. Create docs on client and server.
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "client_replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
        db_obj_server.create_bulk_docs(num_of_docs, "server_replication", db=cbl_db_server, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "client_replication", db=cbl_db_client, channels=channels)
        db_obj_server.create_bulk_docs(num_of_docs, "server_replication", db=cbl_db_server, channels=channels)

    # Now set up client
    # 2. Start the server and start replication from client with push and pull.
    repl_config = p2p_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       push_filter=True, pull_filter=True, filter_callback_func='boolean',
                                       replication_type="push_pull", endPointType=endpoint_type)
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    total = replicator.getTotal(repl_config)
    completed = replicator.getCompleted(repl_config)
    assert total == completed, "replication from client to server did not completed " + \
                               str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == 2 * num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl_config)

    client_doc_ids = db_obj_client.getDocIds(cbl_db_client)
    server_doc_ids = db_obj_server.getDocIds(cbl_db_server)

    # 3. Verify replication is completed.
    assert sorted(client_doc_ids) == sorted(server_doc_ids), "Replication failed. Server db doesn't have same docs"
    server_docs = db_obj_server.getDocuments(cbl_db_server, server_doc_ids)

    # 4. Add new fields to docs and restart the replication with the same configuration.
    updated_docs = {}
    for doc_id in server_docs:
        doc_body = add_new_fields_to_doc(server_docs[doc_id])
        updated_docs[doc_id] = doc_body
        db_obj_server.updateDocument(cbl_db_server, doc_body, doc_id)

    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    replicator.stop(repl_config)

    server_docs_count = db_obj_server.getCount(cbl_db_server)
    client_docs_count = db_obj_client.getCount(cbl_db_client)
    assert server_docs_count == client_docs_count, "Number of docs is not equivalent to number of docs in server "

    client_docs = db_obj_client.getDocuments(cbl_db_client, client_doc_ids)

    # 5. Verify that docs with "new_field_1" to true only got replicated to other side.
    for doc_id in client_docs:
        if updated_docs[doc_id]["new_field_1"]:
            assert client_docs[doc_id]["new_field_1"] == updated_docs[doc_id]["new_field_1"] and\
                client_docs[doc_id]["new_field_2"] == updated_docs[doc_id]["new_field_2"] and\
                client_docs[doc_id]["new_field_3"] == updated_docs[doc_id]["new_field_3"],\
                "Filter stopped the replication for the valid case "
        else:
            assert "new_field_1" not in client_docs[doc_id] and "new_field_2" not in client_docs[doc_id] and\
                   "new_field_3" not in client_docs[doc_id], "Filter didn't stop replication of docs with" \
                                                             " new_field_1 to False"
    if endpoint_type == "URLEndPoint":
        peer_to_peer_server.server_stop(replicator_tcp_listener, endpoint_type)


@pytest.mark.listener
@pytest.mark.hydrogen
def test_p2p_delete_db_active_replicator_and_live_query(params_from_base_test_setup):
    """
        @summary:
        1. create a db on cbls
        2. start 2 replicators, ensure one of the replicator is push_pull replicator with continues=true
        3. if live_query_enabled, register a live query to the cbl db, otherwise, skip this step
        4. close the cbl db
        5. verify cbl db is closed closed successfully
    """
    base_url_list = params_from_base_test_setup["base_url_list"]
    host_list = params_from_base_test_setup["host_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
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

    # 1a. create a db, and add document to the cbl db. Creating new DB
    db = Database(base_url_list[0])
    db_name = "test_delete_db_" + str(time.time())
    log_info("Creating a Database {} at test setup".format(db_name))
    db_config = db.configure()
    cbl_db = db.create(db_name, db_config)

    server_host = host_list[0]
    num_of_docs = 10000
    # 1a. create a db, and add document to the cbl db
    db_obj_server.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db, channels=channel)
    peer_to_peer_server = PeerToPeer(base_url_list[0])

    listener = peer_to_peer_server.server_start(cbl_db)
    url_listener_port = peer_to_peer_server.get_url_listener_port(listener)

    # 2 Now set up replicator on the server/listener DB
    repl1 = peerToPeer_client1.configure(port=url_listener_port, host=server_host, server_db_name=db_name,
                                         client_database=cbl_db_client1, continuous=True,
                                         replication_type="pull_push", endPointType="URLEndPoint")
    peerToPeer_client1.client_start(repl1)
    repl2 = peerToPeer_client2.configure(port=url_listener_port, host=server_host, server_db_name=db_name,
                                         client_database=cbl_db_client2, continuous=True,
                                         replication_type="pull_push", endPointType="URLEndPoint")
    peerToPeer_client2.client_start(repl2)

    # 3. register a live query to the cbl db
    qy = Query(base_url_list[0])
    query = qy.query_selectAll(cbl_db_server)
    query_listener = qy.addChangeListener(query)

    log_info(client_replicator1.getActivitylevel(repl1))
    log_info(client_replicator2.getActivitylevel(repl2))

    try:
        log_info("deleting database")
        db.deleteDB(cbl_db)
        log_info("database is deleted successfully")
        assert True
    except KeyError:
        qy.removeChangeListener(query_listener)
        assert False, "deleting database with active replicators are failed"
    peer_to_peer_server.server_stop(listener, "URLEndPoint")
