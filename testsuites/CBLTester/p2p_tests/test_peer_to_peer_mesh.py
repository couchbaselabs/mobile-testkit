import time
import random
import pytest

from concurrent.futures import ThreadPoolExecutor
from keywords.utils import log_info
from keywords import attachment
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from CBLClient.PeerToPeer import PeerToPeer



#
# @pytest.mark.listener
# @pytest.mark.parametrize("num_of_docs, continuous, replicator_type, attachments, endPointType", [
#     (10, True, "push_pull", False, "URLEndPoint"),
#     (100, True, "push_pull", True, "MessageEndPoint"),
#     (10, True, "push", True, "MessageEndPoint"),
#     (100, False, "push", False, "URLEndPoint"),
# ])
# def test_peer_to_peer_very_peer_is_listener_and_replicator_with_mesh(params_from_base_test_setup, server_setup, num_of_docs, continuous, replicator_type, attachments, endPointType):
#     """
#         @summary: peer1<-> Peer2, Peer1 <->Peer3, Peer2<->peer1, Peer2<->Peer3
#         1. Create docs on peer1.
#         2. Start the peer2.
#         3. Start replication from peer1.
#         4. Verify replication is completed.
#         5. Verify all docs got replicated on peer2
#         6. Create docs on peer2
#         7. Start replication from peer2.
#         8. Verify replication is completed.
#         9. Verify all docs got replicated on peer1
#     """
#     host_list = params_from_base_test_setup["host_list"]
#     db_obj_list = params_from_base_test_setup["db_obj_list"]
#     db_name_list = params_from_base_test_setup["db_name_list"]
#     base_url_list = server_setup["base_url_list"]
#     cbl_db_server = server_setup["cbl_db_server"]
#     cbl_db_list = server_setup["cbl_db_list"]
#     channels = ["peerToPeer"]
#
#     peer1_replicator = Replication(base_url_list[0])
#     peer2_replicator = Replication(base_url_list[1])
#     peer3_replicator = Replication(base_url_list[2])
#
#     peerToPeer_peer1 = PeerToPeer(base_url_list[0])
#     peerToPeer_peer2 = PeerToPeer(base_url_list[1])
#     peerToPeer_peer3 = PeerToPeer(base_url_list[2])
#
#     db_obj_peer1 = db_obj_list[0]
#     db_obj_peer2 = db_obj_list[1]
#     db_obj_peer3 = db_obj_list[2]
#     cbl_db_peer1 = cbl_db_list[1]
#     cbl_db_peer2 = cbl_db_list[0]
#     cbl_db_peer3 = cbl_db_list[2]
#     db_name_peer1 = db_name_list[0]
#     db_name_peer2 = db_name_list[1]
#     db_name_peer3 = db_name_list[2]
#
#     peer1_host = host_list[0]
#     peer2_host = host_list[1]
#     peer3_host = host_list[2]
#
#     if attachments:
#         db_obj_peer1.create_bulk_docs(num_of_docs, "replication", db=cbl_db_peer1, channels=channels, attachments_generator=attachment.generate_png_100_100)
#     else:
#         db_obj_peer1.create_bulk_docs(num_of_docs, "replication", db=cbl_db_peer1, channels=channels)
#
#     # Now set up peer1 replicators
#     repl = peerToPeer_peer1.configure(host=peer2_host, server_db_name=db_name_peer2, client_database=cbl_db_peer1, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
#     peerToPeer_peer1.client_start(repl)
#     peer1_replicator.wait_until_replicator_idle(repl)
#
#     repl2 = peerToPeer_peer1.configure(host=peer3_host, server_db_name=db_name_peer3, client_database=cbl_db_peer1, continuous=continuous, replication_type=replicator_type, endPointType=endPointType)
#     peerToPeer_peer1.client_start(repl2)
#     peer1_replicator.wait_until_replicator_idle(repl2)
#
#     total = peer1_replicator.getTotal(repl)
#     completed = peer1_replicator.getCompleted(repl)
#
#     assert total == completed, "replication from peer1 to peer2 did not completed " + str(total) + " not equal to " + str(completed)
#     server_docs_count = db_obj_peer2.getCount(cbl_db_peer2)
#     assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in peer2 "
#
#     peer1_replicator.wait_until_replicator_idle(repl)
#     peer1_replicator.wait_until_replicator_idle(repl2)
#     total = peer1_replicator.getTotal(repl)
#     completed = peer1_replicator.getCompleted(repl)
#     assert total == completed, "replication from peer1 to peer2 did not completed " + total + " not equal to " + completed
#     server_docs_count1 = db_obj_peer2.getCount(cbl_db_peer2)
#     server_docs_count2 = db_obj_peer3.getCount(cbl_db_peer3)
#     assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in peer2 "
#     assert server_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in peer3 "
#     peer1_replicator.stop(repl)
#     peer2_replicator.stop(repl2)
#
#
#     # Now set up peer2 replicators
#     repl3 = peerToPeer_peer2.configure(host=peer2_host, server_db_name=db_name_peer2, client_database=cbl_db_peer1,
#                                        continuous=continuous, replication_type=replicator_type,
#                                        endPointType=endPointType)
#     peerToPeer_peer2.client_start(repl3)
#     peer2_replicator.wait_until_replicator_idle(repl3)
#
#     repl4 = peerToPeer_peer2.configure(host=peer3_host, server_db_name=db_name_peer3, client_database=cbl_db_peer1,
#                                         continuous=continuous, replication_type=replicator_type,
#                                         endPointType=endPointType)
#     peerToPeer_peer2.client_start(repl4)
#     peer2_replicator.wait_until_replicator_idle(repl4)
#
#     assert total == completed, "replication from peer2 to peer1 did not completed " + str(total) + " not equal to " + str(completed)
#     server_docs_count = db_obj_peer2.getCount(cbl_db_peer2)
#     assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in peer2 "
#
#     peer1_replicator.wait_until_replicator_idle(repl)
#     peer1_replicator.wait_until_replicator_idle(repl2)
#     total = peer1_replicator.getTotal(repl)
#     completed = peer1_replicator.getCompleted(repl)
#     assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
#     server_docs_count1 = db_obj_peer2.getCount(cbl_db_peer2)
#     server_docs_count2 = db_obj_peer3.getCount(cbl_db_peer3)
#     assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in peer1 "
#     assert server_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in server3 "
#     peer1_replicator.stop(repl)
#     peer2_replicator.stop(repl2)
#
#     # Now set up peer3 replicators
#     repl5 = peerToPeer_peer3.configure(host=peer2_host, server_db_name=db_name_peer2, client_database=cbl_db_peer1,
#                                        continuous=continuous, replication_type=replicator_type,
#                                        endPointType=endPointType)
#     peerToPeer_peer3.client_start(repl5)
#     peer3_replicator.wait_until_replicator_idle(repl5)
#
#     repl6 = peerToPeer_peer3.configure(host=peer2_host, server_db_name=db_name_peer2, client_database=cbl_db_peer1,
#                                         continuous=continuous, replication_type=replicator_type,
#                                         endPointType=endPointType)
#     peerToPeer_peer3.client_start(repl6)
#     peer3_replicator.wait_until_replicator_idle(repl6)
#
#     assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
#     server_docs_count1 = db_obj_peer2.getCount(cbl_db_peer2)
#     server_docs_count2 = db_obj_peer3.getCount(cbl_db_peer3)
#     assert server_docs_count1 == num_of_docs, "Number of docs is not equivalent to number of docs in server1 "
#     assert server_docs_count2 == num_of_docs, "Number of docs is not equivalent to number of docs in server2 "
#     peer1_replicator.stop(repl)
#     peer2_replicator.stop(repl2)
#
#
#     replicatorTcpListener1 = peerToPeer_peer1.server_start(cbl_db_peer1)
#     replicatorTcpListener2 = peerToPeer_peer2.server_start(cbl_db_peer2)
#     replicatorTcpListener3 = peerToPeer_peer3.server_start(cbl_db_peer3)
#
#     peerToPeer_peer1.server_stop(replicatorTcpListener1)
#     peerToPeer_peer2.server_stop(replicatorTcpListener2)
#     log_info("servers starting .....")
#
#     # Now setup server
#     server_repl = peerToPeer_client.configure(host=peer1_host, server_db_name=db_name_peer1,
#                                               client_database=cbl_db_peer2, continuous=continuous,
#                                               replication_type=replicator_type, endPointType=endPointType)
#     peerToPeer_client.client_start(server_repl)
#     replicator.wait_until_replicator_idle(server_repl)
#
#     total = replicator.getTotal(server_repl)
#     completed = replicator.getCompleted(server_repl)
#     assert total == completed, "replication from server to client did not completed " + str(total) + " not equal to " + str(completed)
#     server_docs_count = db_obj_server.getCount(cbl_db_server)
#     assert server_docs_count == num_of_docs + num_of_docs, "Number of docs is not equivalent to number of docs in server "
#
#     replicator.stop(server_repl)
#     replicator.stop(repl)
