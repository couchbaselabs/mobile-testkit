import pytest
import time
import random

from keywords.utils import log_info, add_new_fields_to_doc
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endpoint_type", [
    (10, True, "push_pull", False, "URLEndPoint"),
    # (100, True, "push_pull", True, "MessageEndPoint"),
    # (10, True, "push_pull", False, "MessageEndPoint"),
    # (100, False, "push", False, "URLEndPoint"),
])
def test_p2p_replication_push_filtering(params_from_base_test_setup, server_setup, num_of_docs, continuous,
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
    if attachments:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)
    else:
        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels)

    # Now set up client
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=continuous,
                                       replication_type=replicator_type, endPointType=endpoint_type)
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
    updates_in_doc = {}
    client_docs = db_obj_client.getDocuments(cbl_db_client, client_doc_ids)
    for doc_id, doc_body in client_docs.items():
        doc_body = add_new_fields_to_doc(doc_body)
        updates_in_doc[doc_id] = {
            "new_field_1": doc_body["new_field_1"],
            "new_field_2": doc_body["new_field_2"],
            "new_field_3": doc_body["new_field_3"],
        }
        db_obj_client.updateDocument(database=cbl_db_client, data=doc_body, doc_id=doc_id)

    # 4. The replication will have filter for newly added field
    # Docs with new_field_1 value to true will only be replicated, others will be rejected by filter method
    repl_config = p2p_client.configure(host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=False,
                                       replication_type="push", endPointType=endpoint_type,
                                       push_filter=True, filter_callback_func='boolean')
    replicator.start(repl_config)
    replicator.wait_until_replicator_idle(repl_config)
    replicator.stop(repl_config)

    # 4. Verify SG has new fields added only when "new_field_1" is true
    server_docs = db_obj_server.getDocuments(cbl_db_server, server_doc_ids)
    client_docs = db_obj_client.getDocuments(cbl_db_client, client_doc_ids)

    for doc_id in server_docs:
        key = server_docs[doc_id]
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