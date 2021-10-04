
import pytest

from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.ListenerAuthenticator import ListenerAuthenticator


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, endPointType", [
    (10, True, "push_pull", "URLEndPoint"),
    (10, False, "push_pull", "URLEndPoint"),
    (10, True, "push", "URLEndPoint"),
    (10, False, "push", "URLEndPoint")
])
def test_peer_to_peer_with_basic_auth(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on client.
        2. Start the server with username and password.
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
    listener = ListenerAuthenticator(base_url_list[0])

    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]

    listener_auth = listener.create("testkit", "pass")
    replicator_auth = BasicAuthenticator(base_url_client)
    replicator_key = replicator_auth.create("testkit", "pass")

    replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server, basic_auth=listener_auth)
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    repl = peerToPeer_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                       continuous=continuous, replication_type=replicator_type,
                                       endPointType=endPointType, basic_auth=replicator_key)
    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peer_to_peer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.p2p
@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint")
])
def test_peer_to_peer_with_basic_auth_incorrect_pass(params_from_base_test_setup, server_setup, continuous, replicator_type, endPointType):
    """
        @summary:
        1. Create docs on client.
        2. Start the server with username and password.
        3. Start replication from client.
        4. Verify replication is failed to start with unauthorized errors.
    """
    host_list = params_from_base_test_setup["host_list"]
    db_name_list = params_from_base_test_setup["db_name_list"]
    base_url_list = server_setup["base_url_list"]
    cbl_db_server = server_setup["cbl_db_server"]
    cbl_db_list = server_setup["cbl_db_list"]
    base_url_client = base_url_list[1]
    replicator = Replication(base_url_client)
    peerToPeer_client = PeerToPeer(base_url_client)
    cbl_db_client = cbl_db_list[1]
    db_name_server = db_name_list[0]
    peerToPeer_server = PeerToPeer(base_url_list[0])
    listener = ListenerAuthenticator(base_url_list[0])

    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    listener_auth = listener.create("testkit", "pa")
    replicator_auth = BasicAuthenticator(base_url_client)
    replicator_key = replicator_auth.create("testkit", "pass")

    replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server, basic_auth=listener_auth)
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)

    # Now set up client
    repl = peerToPeer_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                       continuous=continuous, replication_type=replicator_type,
                                       endPointType=endPointType, basic_auth=replicator_key)
    peerToPeer_client.client_start(repl)
    try:
        replicator.wait_until_replicator_idle(repl)
    except Exception as he:
        assert 'unauthorized' in str(he).lower()
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)

    # incorrect username
    listener_auth = listener.create("testkt", "pass")
    replicator_auth = BasicAuthenticator(base_url_client)
    replicator_key = replicator_auth.create("testkit", "pass")

    replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server, basic_auth=listener_auth)
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)

    # Now set up client
    repl = peerToPeer_client.configure(port=url_listener_port, host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client,
                                       continuous=continuous, replication_type=replicator_type,
                                       endPointType=endPointType, basic_auth=replicator_key)
    peerToPeer_client.client_start(repl)
    try:
        replicator.wait_until_replicator_idle(repl)
    except Exception as he:
        assert 'unauthorized' in str(he).lower()
        peerToPeer_server.server_stop(replicator_tcp_listener, endPointType)
        return
    assert False, "We need to get unauthorized errors"
