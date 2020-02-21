import random

import pytest

from keywords.utils import add_new_fields_to_doc, meet_supported_version
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


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
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    version_list = params_from_base_test_setup["version_list"]
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

    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")

    server_host = host_list[0]
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    # Now set up client
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
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
        for doc_id, doc_body in client_docs.items():
            doc_body = add_new_fields_to_doc(doc_body)
            db_obj_client.updateDocument(database=cbl_db_client, data=doc_body, doc_id=doc_id)
    else:
        push_filter = False
        pull_filter = True
        server_docs = db_obj_server.getDocuments(cbl_db_server, server_doc_ids)
        for doc_id, doc_body in server_docs.items():
            doc_body = add_new_fields_to_doc(doc_body)
            db_obj_server.updateDocument(database=cbl_db_server, data=doc_body, doc_id=doc_id)

    # 4. The replication will have filter for newly added field
    # Docs with new_field_1 value to true will only be replicated, others will be rejected by filter method
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       replication_type=replicator_type, endPointType=endpoint_type,
                                       push_filter=push_filter, pull_filter=pull_filter,
                                       filter_callback_func='boolean')
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    replicator.stop(repl_config)

    # 4. Verify SG has new fields added only when "new_field_1" is true
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
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    version_list = params_from_base_test_setup["version_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    channels = ["peerToPeer"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)
    num_of_docs_to_delete = (num_of_docs * 2) / 10

    p2p_client = PeerToPeer(base_url_client)
    db_obj_server = db_obj_list[0]
    cbl_db_client = cbl_db_list[1]
    db_obj_client = db_obj_list[1]
    db_name_server = db_name_list[0]

    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")

    server_host = host_list[0]
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
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
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
    client_doc_ids_to_delete = random.sample(client_ids, num_of_docs_to_delete / 2)
    server_doc_ids_to_delete = random.sample(server_ids, num_of_docs_to_delete / 2)

    db_obj_server.delete_bulk_docs(database=cbl_db_server, doc_ids=server_doc_ids_to_delete)
    db_obj_client.delete_bulk_docs(database=cbl_db_client, doc_ids=client_doc_ids_to_delete)

    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
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
    host_list = params_from_base_test_setup["host_list"]
    db_obj_list = params_from_base_test_setup["db_obj_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    version_list = params_from_base_test_setup["version_list"]
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

    if meet_supported_version(version_list, "2.5.0") is False:
        pytest.skip("Filtering feature is available only onwards CBL 2.5.0")

    server_host = host_list[0]
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
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
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
