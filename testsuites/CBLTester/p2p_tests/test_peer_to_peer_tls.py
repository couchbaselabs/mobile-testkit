
import pytest

from keywords.utils import log_info
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer

@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint"),
    (False, "push", "URLEndPoint")
])
# SELF SIGNED WITH serverCertificateVerificationMode
def test_peer_to_peer_tls_basic_certs(params_from_base_test_setup, server_setup, continuous, replicator_type, endPointType):
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
    replicator_tcp_listener = server_setup["replicator_tcp_listener"]
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
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50
    # listener = ListenerAuthenticator(base_url_list[0])
    # listener_auth = listener.listenerCertificateAuthenticator_create
    replicatorTcpListener = peer_to_peer_server.server_start(cbl_db_server, tls_disable=False, tls_auth_type="self_signed")
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicatorTcpListener)

    # replicator_tls_auth = BasicAuthenticator(base_url_client)
    # replicator_certs = replicator_tls_auth.tlsAuthenticator_create

    #db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels, attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                       continuous=continuous, replication_type=replicator_type,
                                       endPointType=endPointType, tls_auth_type="self_signed", port=url_listener_port,
                                       tls_disable=False)
    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    # total = replicator.getTotal(repl)
    # completed = replicator.getCompleted(repl)
    # assert total == completed, "replication from client to server did not completed " + str(total) + " not equal to " + str(completed)
    # server_docs_count = db_obj_server.getCount(cbl_db_server)
    # assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peer_to_peer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint")
    # ,
    # (True, "push_pull", "MessageEndPoint"),
    # (False, "pull", "MessageEndPoint"),
    # (False, "push", "URLEndPoint"),
])
def test_peer_to_peer_enable_with_certs_authenticator(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                          endPointType):
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
        replicator_tcp_listener = server_setup["replicator_tcp_listener"]
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
        peerToPeer_server = PeerToPeer(base_url_list[0])
        peerToPeer_server.server_stop(replicator_tcp_listener)

        server_host = host_list[0]
        num_of_docs = 50

        replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server, tls_enable=True, using_authenticator=True,
                                                               tls_self_signed=True)

        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)

        # Now set up client
        repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client, continuous=continuous,
                                           replication_type=replicator_type, endPointType=endPointType,
                                           server_certs=replicatorTcpListener, port=5010, tls=True,
                                           using_authenticator=True, tls_self_signed=True)
        peerToPeer_client.client_start(repl)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "replication from client to server did not completed " + str(
            total) + " not equal to " + str(completed)
        server_docs_count = db_obj_server.getCount(cbl_db_server)
        assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
        replicator.stop(repl)
        peerToPeer_server.server_stop(replicator_tcp_listener)



@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint"),
    (True, "push_pull", "MessageEndPoint"),
    (False, "pull", "MessageEndPoint"),
    (False, "push", "URLEndPoint"),
])
def test_peer_to_peer_enable_tls_with_any_selfsigned(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                          endPointType):
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
        replicator_tcp_listener = server_setup["replicator_tcp_listener"]
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
        peerToPeer_server = PeerToPeer(base_url_list[0])
        peerToPeer_server.server_stop(replicator_tcp_listener)

        server_host = host_list[0]
        num_of_docs = 50
        # listener = ListenerAuthenticator(base_url_list[0])
        # lister_auth = listener.listenerCertificateAuthenticator_create
        replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server, tls_enable=True)

        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)

        # Now set up client
        repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client, continuous=continuous,
                                           replication_type=replicator_type, endPointType=endPointType,
                                           any_self_signed=True, port=5010, tls=True)
        peerToPeer_client.client_start(repl)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "replication from client to server did not completed " + str(
            total) + " not equal to " + str(completed)
        server_docs_count = db_obj_server.getCount(cbl_db_server)
        assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
        replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint"),
    (True, "push_pull", "MessageEndPoint"),
    (False, "pull", "MessageEndPoint"),
    (False, "push", "URLEndPoint"),
])
def test_peer_to_peer_tls_self_signed_certs(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                          endPointType):
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
        replicator_tcp_listener = server_setup["replicator_tcp_listener"]
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
        peerToPeer_server = PeerToPeer(base_url_list[0])
        peerToPeer_server.server_stop(replicator_tcp_listener)

        server_host = host_list[0]
        num_of_docs = 50
        replicatorTcpListener = peerToPeer_server.server_start(cbl_db_server, tls_enable=True,
                                                               tls_self_signed=True)

        db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                       attachments_generator=attachment.generate_png_100_100)

        # Now set up client
        repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client, continuous=continuous,
                                           replication_type=replicator_type, endPointType=endPointType,
                                           port=5010, tls=True, tls_self_signed=True)
        peerToPeer_client.client_start(repl)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "replication from client to server did not completed " + str(
            total) + " not equal to " + str(completed)
        server_docs_count = db_obj_server.getCount(cbl_db_server)
        assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
        replicator.stop(repl)