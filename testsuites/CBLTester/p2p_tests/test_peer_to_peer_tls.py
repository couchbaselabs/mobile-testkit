import pytest

from keywords.utils import log_info
from keywords import attachment
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer


@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType, tls, servercerts", [
    (True, "push_pull", "URLEndPoint", False, True),
    (False, "push", "URLEndPoint", False, False),
    (False, "push", "URLEndPoint", False, True),
    (True, "push_pull", "URLEndPoint", False, False),

])
def test_peer_to_peer_tls_basic_certs(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                      endPointType, tls, servercerts):
    """
        @summary:
        1. Create docs on server.
        2. Start the server with self signed certs / tls disable
        3. Start replication from client.with valied self signed/ without self signed/ server verification mode
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
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50

    # We want to use test tls_disable property on the Listener side only
    replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server, tls_disable=tls, tls_auth_type="self_signed",)
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                   attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    if servercerts:
        repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client,
                                           continuous=continuous, replication_type=replicator_type,
                                           endPointType=endPointType, port=url_listener_port,
                                           tls_disable=False, tls_auth_type="self_signed")


        peerToPeer_client.client_start(repl)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "replication from client to server did not completed " + str(
            total) + " not equal to " + str(completed)
        server_docs_count = db_obj_server.getCount(cbl_db_server)
        assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
        replicator.stop(repl)

        # Start the server with the replicator verification mode.
        repl2 = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                           client_database=cbl_db_client,
                                           continuous=continuous, replication_type=replicator_type,
                                           endPointType=endPointType, port=url_listener_port,
                                           tls_disable=False, tls_auth_type="self_signed", server_verification_mode=True)

        peerToPeer_client.client_start(repl2)
        replicator.wait_until_replicator_idle(repl2)
        peer_to_peer_server.server_stop(replicator_tcp_listener, endPointType)
    else:
        try:
            repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                               client_database=cbl_db_client,
                                               continuous=continuous, replication_type=replicator_type,
                                               endPointType=endPointType, port=url_listener_port,
                                               tls_disable=False)
            peerToPeer_client.client_start(repl)
            replicator.wait_until_replicator_idle(repl)
        except Exception as he:
            # OR condition Add to support the Android
            assert "The certificate does not terminate in a trusted root CA" in str(he) or "server TLS certificate untrusted" in str(he)
        finally:
            peer_to_peer_server.server_stop(replicator_tcp_listener, endPointType)
            return
        assert False, "replicator started with self_signed"



@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint"),
    (False, "push", "URLEndPoint"),
])
def test_peer_to_peer_enable_with_certs_authenticator(params_from_base_test_setup, server_setup, continuous,
                                                      replicator_type,
                                                      endPointType):
    """
        @summary:
        1. Start the server with the  Root certs with authenticator.
        2. Start replication with client certs using the authenticator.
        3. Verify replication is completed.
        4. Verify all docs got replicated on server
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
    peerToPeer_server = PeerToPeer(base_url_list[0])
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    print(message_url_tcp_listener)
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50

    url_listener = peerToPeer_server.server_start(cbl_db_server, tls_disable=False, tls_authenticator=True)
    url_listener_port = peer_to_peer_server.get_url_listener_port(url_listener)

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                   attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=continuous,
                                       replication_type=replicator_type, endPointType=endPointType,
                                       port=url_listener_port, tls_disable=False,
                                       tls_authenticator=True)
    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(
        total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peerToPeer_server.server_stop(url_listener, replicator_type)


# need to test with out tls enable
@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType", [
    (True, "push_pull", "URLEndPoint"),
    (False, "push", "URLEndPoint"),
])
def test_peer_to_peer_enable_tls_with_any_selfsigned_and_authenticator(params_from_base_test_setup, server_setup,
                                                                       continuous, replicator_type,
                                                                       endPointType):
    """
        @summary:
        2. Start the server with the self signed certs and Root certs.
        3. Start replication with client certs and selfsigned.
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
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50
    # listener = ListenerAuthenticator(base_url_list[0])
    # listener_auth = listener.listenerCertificateAuthenticator_create
    replicator_tcp_listener = peer_to_peer_server.server_start(cbl_db_server, tls_disable=False,
                                                               tls_auth_type="self_signed", tls_authenticator=True)
    url_listener_port = peer_to_peer_server.get_url_listener_port(replicator_tcp_listener)

    # replicator_tls_auth = BasicAuthenticator(base_url_client)
    # replicator_certs = replicator_tls_auth.tlsAuthenticator_create

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                   attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client,
                                       continuous=continuous, replication_type=replicator_type,
                                       endPointType=endPointType, tls_auth_type="self_signed", port=url_listener_port,
                                       tls_disable=False, tls_authenticator=True)
    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(
        total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peer_to_peer_server.server_stop(replicator_tcp_listener, endPointType)


@pytest.mark.listener
@pytest.mark.parametrize("continuous, replicator_type, endPointType, with_certs", [
    (True, "push_pull", "URLEndPoint", True),
    (False, "push", "URLEndPoint", True),
    (True, "push", "URLEndPoint", False),
    (False, "push_pull", "URLEndPoint", False),
])
def test_peer_to_peer_tls_any_self_signed_certs_create(params_from_base_test_setup, server_setup, continuous, replicator_type,
                                                endPointType, with_certs):
    """
        @summary:
        1. Start the server with the self signed certs using the create identity api.
        2. Start replication with AcceptOnlySelfSignedServerCertificate.
        3. Verify replication is completed.
        4. Verify all docs got replicated on server
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
    peerToPeer_server = PeerToPeer(base_url_list[0])
    peer_to_peer_server = PeerToPeer(base_url_list[0])
    message_url_tcp_listener = server_setup["message_url_tcp_listener"]
    print(message_url_tcp_listener)
    peer_to_peer_server.server_stop(message_url_tcp_listener, "MessageEndPoint")

    server_host = host_list[0]
    num_of_docs = 50

    if with_certs:
        url_listener = peerToPeer_server.server_start(cbl_db_server, tls_disable=False, tls_auth_type="self_signed_create")
    else:
        url_listener = peerToPeer_server.server_start(cbl_db_server, tls_disable=False)
    url_listener_port = peer_to_peer_server.get_url_listener_port(url_listener)

    db_obj_client.create_bulk_docs(num_of_docs, "replication", db=cbl_db_client, channels=channels,
                                   attachments_generator=attachment.generate_png_100_100)

    # Now set up client
    repl = peerToPeer_client.configure(host=server_host, server_db_name=db_name_server,
                                       client_database=cbl_db_client, continuous=continuous,
                                       replication_type=replicator_type, endPointType=endPointType,
                                       port=url_listener_port, tls_disable=False,
                                       server_verification_mode=True)
    peerToPeer_client.client_start(repl)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + str(
        total) + " not equal to " + str(completed)
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)
    peerToPeer_server.server_stop(url_listener, replicator_type)
