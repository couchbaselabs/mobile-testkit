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
@pytest.mark.parametrize("num_of_docs, continuous, replicator_type, authenticator_type", [
    (10, True, "push_pull", "basic"),
    (10, False, "push_pull", "session"),
    (100, True, "push", "basic"),
    # (100, False, "pull", "session"),
])
def test_peer_to_peer_1to1_valid_values(params_from_base_suite_setup, num_of_docs, continuous, replicator_type, authenticator_type):
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
    db_obj_client.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_client, channels=channel)
    peerToPeer_server.server_start(cbl_db_server)
    log_info("server starting .....")

    # Now set up client
    repl = peerToPeer_client.client_start(host=server_host, server_db_name=db_name_server, client_database=cbl_db_client, continuous=continuous, authenticator=replicator_authenticator, replication_type=replicator_type)
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    assert total == completed, "replication from client to server did not completed " + total + " not equal to " + completed
    server_docs_count = db_obj_server.getCount(cbl_db_server)
    assert server_docs_count == num_of_docs, "Number of docs is not equivalent to number of docs in server "
    replicator.stop(repl)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize("num_of_docs, continuous, authenticator_type", [
    (10, True, "basic"),
    (10, False, "session"),
    (100, True, "basic"),
    # (100, False, "pull", "session"),
])
def test_peer_to_peer_1to1_pull_replication(params_from_base_suite_setup, num_of_docs, continuous, authenticator_type):
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
