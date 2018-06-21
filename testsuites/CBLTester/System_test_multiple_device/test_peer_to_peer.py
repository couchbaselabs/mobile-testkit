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
def test_peer_to_peer_iosAndroid(params_from_base_suite_setup):
    """
        @summary:
        1. Enable allow_conflicts = true in SG config or do not set allow_conflicts
        2. Create docs on CBL.
        3. Update the doc few times.
        4. Do push replication to SG
        5. Create conflict on SG
        6. Do pull replication to CBL.
        7. Check the revision list for the doc
    """
    sg_db = "db"
    sg_url = params_from_base_suite_setup["sg_url"]
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_mode = params_from_base_suite_setup["mode"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    num_of_docs = 10
    channels = ["ABC"]
    # db = params_from_base_suite_setup["db"]
    # cbl_db = params_from_base_suite_setup["source_db"]   
    base_url_list = params_from_base_suite_setup["base_url_list"]
    socket_host_list = params_from_base_suite_setup["socket_host_list"]
    socket_port_list = params_from_base_suite_setup["socket_port_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    username = "autotest"
    password = "password"
    channel = ["peerToPeer"]

    # Reset cluster to ensure no data in system
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channel)
    base_url_ios = base_url_list[1]
    # base_url_android = base_url_list[0]
    base_url_ios2 = base_url_list[0]

    peerToPeer_ios = PeerToPeer(base_url_ios)
    # peerToPeer_android = PeerToPeer(base_url_ios2)
    peerToPeer_ios2 = PeerToPeer(base_url_ios2)
    # for base_url in zip(base_url_list):
    cbl_db_ios2 = cbl_db_list[0]
    db_obj_ios2 = db_obj_list[0]
    cbl_db_ios = cbl_db_list[1]
    db_obj_ios = db_obj_list[1]
    
    ios_host = socket_host_list[0]
    ios_port = socket_port_list[0]
    # android_host = socket_host_list[0]
    # android_port = socket_port_list[0]
    print "base url list ", base_url_list
    # base_url_android = base_url_list[0]
    base_url_ios2 = base_url_list[0]

    db_obj_ios.create_bulk_docs(num_of_docs, "cbl-peerToPeer", db=cbl_db_ios, channels=channel)
    ios_port_re = int(ios_port)
    # server = peerToPeer_android.socket_connection(ios_port_re)
    server = peerToPeer_ios2.socket_connection(ios_port_re)
    peerToPeerObj = peerToPeer_ios.peer_intialize(cbl_db_ios, False, ios_host, ios_port)
    """with ThreadPoolExecutor(max_workers=1) as tpe:
        android_connection = tpe.submit(
            peerToPeer_android.socket_connection,
            android_port1
        )
        ios_connection = tpe.submit(
            peerToPeer_ios.peer_intialize,
            cbl_db_android,
            False,
            android_host,
            android_port
        )

        android_connection.result()
        ios_connection.result()
    """

    # peerToPeer_android.accept_client(server)
    print " going to start ios peer to peer"
    peerToPeer_ios.start(peerToPeerObj)
    print " going to read data fraom client by android"
    peerToPeer_ios.stop(peerToPeerObj)
    count = db_obj_ios2.getCount(cbl_db_ios2)
    print "count for android is ", count
    count1 = db_obj_ios.getCount(cbl_db_ios)
    print "count for ios is ", count1
    # peerToPeer_android.read_data_fromClient(socket)
