import pytest
import time
import os
import json
import concurrent.futures

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, \
    load_sync_gateway_config
from keywords.ClusterKeywords import ClusterKeywords

from keywords.MobileRestClient import MobileRestClient
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords import document, attachment


@pytest.mark.syncgateway
@pytest.mark.attachment_cleanup
def test_upgrade_delete_attachments(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive :https://docs.google.com/spreadsheets/d/1RrrIcIZN7MgLDlNzGWfUHo2NTYrx1Jr55SBNeCdDUQs/edit#gid=0
    1.Create the documents with attachments in the older version(2.8-1.5) of SG, and delete few documents
 then upgrade the SG .
Edit the doc by adding more attachements to the document then delete the documents.
Verify newly added attachments
 are completely deleted.
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sync_gateway_previous_version = params_from_base_test_setup['sync_gateway_previous_version']
    mode = params_from_base_test_setup['mode']
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_obj = SyncGateway()

    # sg_platform = params_from_base_test_setup['sg_platform']
    username = "autotest"
    password = "password"
    sg_channels = ["attachments-cleanup"]
    remote_db = "db"

    # 1. Have prelithium config
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')
    sg_conf_name = "sync_gateway_default"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    print("*" * 10)
    print(temp_sg_config)
    print("*" * 10)

    cbs_cluster.reset(sg_config_path=temp_sg_config)
    print(cluster_conf)
    print("*" * 10)
    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_previous_version, True)
    print(cluster_conf)
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, remote_db, username, password=password, channels=sg_channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, remote_db, username)
    session = cookie, session_id

    added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com", channels=sg_channels,
                                   auth=session, attachments_generator=attachment.generate_5_png_100_100)

    log_info(added_doc)
    print("* after changing to latest" * 10)

    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_version, True)
    print(cluster_conf)
    print("* after changing to latest" * 10)
    # sg_docs = sg_client.get_all_docs(url=sg_url, db=remote_db, auth=session, include_docs=True)

    for i in range(4):
        sg_client.delete_doc(url=sg_url, db=remote_db, doc_id="att_com_" + i, auth=session)

    attachments = {}
    duplicate_attachments = attachment.load_from_data_dir(["sample_text.txt"])
    for att in duplicate_attachments:
        attachments[att.name] = {"data": att.data}
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com_" + 5, number_updates=1,
                         update_attachment=attachments)

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf,
                                cluster_conf)

    for i in range(6, 8):
        sg_client.delete_doc(url=sg_url, db=remote_db, doc_id="att_com_" + i, auth=session)

    sg_client.compact_attachments(sg_admin_url, "status")
    sg_client.compact_attachments(sg_admin_url, "progress")
    sg_client.compact_attachments(sg_admin_url, "stop")

