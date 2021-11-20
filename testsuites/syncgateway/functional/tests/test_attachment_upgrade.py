import pytest
import time
import os
import json
import concurrent.futures

from keywords.utils import log_info, host_for_url
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, \
    load_sync_gateway_config
from keywords.ClusterKeywords import ClusterKeywords

from keywords.MobileRestClient import MobileRestClient
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from keywords import document, attachment
from utilities.cluster_config_utils import get_cluster
from couchbase.exceptions import DocumentNotFoundException


@pytest.mark.syncgateway
@pytest.mark.attachment_cleanup
def test_upgrade_delete_attachments(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive :https://docs.google.com/spreadsheets/d/1RrrIcIZN7MgLDlNzGWfUHo2NTYrx1Jr55SBNeCdDUQs/edit#gid=0
    1. Create the documents with attachments in the older version(2.8-1.5) of SG,
    2. Delete few documents
    3. upgrade the SG .
    4. Edit the doc by adding more attachments
    5  delete the documents.
    6. Verify newly added attachments
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

    # # 1. Have prelithium config
    print(sync_gateway_version, "sync_gateway_version")
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test can run with sgw version 3.0 and above')
    sg_conf_name = "sync_gateway_default"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)

    cbs_cluster.reset(sg_config_path=temp_sg_config)
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

    added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=1000, id_prefix="att_com", channels=sg_channels,
                                   auth=session, attachments_generator=attachment.generate_5_png_100_100)

    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_version, True)
    for i in range(4):
        doc_id = "att_com_" + str(i)
        latest_rev = sg_client.get_latest_rev(sg_admin_url, remote_db, doc_id, session)
        sg_client.delete_doc(url=sg_admin_url, db=remote_db, doc_id=doc_id, rev=latest_rev, auth=session)

    attachments = {}
    duplicate_attachments = attachment.load_from_data_dir(["sample_text.txt"])
    for att in duplicate_attachments:
        attachments[att.name] = {"data": att.data}
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com_" + str(5), number_updates=1,
                         update_attachment=attachments)

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf,
                                cluster_conf)

    for i in range(6, 8):
        doc_id = "att_com_" + str(i)
        latest_rev = sg_client.get_latest_rev(sg_admin_url, remote_db, doc_id, session)
        sg_client.delete_doc(url=sg_admin_url, db=remote_db, doc_id=doc_id, rev=latest_rev, auth=session)

    duplicate_attachments = attachment.load_from_data_dir(["sample_text.txt"])
    for att in duplicate_attachments:
        attachments[att.name] = {"data": att.data}

    # 5. Create Same attachments in 2 different documents
    doc_9 = "att_com_" + str(9)
    doc_10 = "att_com_" + str(10)
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id=doc_9, number_updates=1,
                         update_attachment=attachments)
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id=doc_10, number_updates=1,
                         update_attachment=attachments)

    updated_attachment_ids = []
    # Get the attachment ID from the document meta data for verification
    raw_doc = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc=doc_9)
    attachments = raw_doc["_attachments"]
    att_names = list(raw_doc["_attachments"].keys())
    for name in att_names:
        attachment_raw = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc=doc_10, attachment=name)
        updated_attachment_ids.append(attachment_raw['key'])

    latest_rev = sg_client.get_latest_rev(sg_admin_url, remote_db, doc_10, session)
    sg_client.delete_doc(url=sg_admin_url, db=remote_db, doc_id=doc_10, rev=latest_rev, auth=session)

    # Verify document 10's sample_text attachment is still present in SG and Couchbase
    assert sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc=doc_9,
                                                attachment="sample_text.txt")

    cluster_topology = params_from_base_test_setup['cluster_topology']
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    if ssl_enabled:
        connection_url = "couchbases://{}?ssl=no_verify".format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    bucket_name = 'data-bucket'
    sdk_client = get_cluster(connection_url, bucket_name)

    sdk_deleted_doc_scratch_pad = list(updated_attachment_ids)
    for doc_id in updated_attachment_ids:
        nfe = None
        with pytest.raises(DocumentNotFoundException) as nfe:
            sdk_client.get(doc_id)
        log_info(nfe.value)
        if nfe is not None:
            sdk_deleted_doc_scratch_pad.remove(nfe.value.key)
    assert len(sdk_deleted_doc_scratch_pad) == 0

    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    sg_client.compact_attachments(sg_admin_url, remote_db, "stop")
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    status = sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"]
    if status == "stopping" or status == "running":
        sg_client.compact_attachments(sg_admin_url, remote_db, "progress")
        time.sleep(5)
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"] == "4956", "compaction count not matching"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["last_error"] == "", "Error found while running the compaction process"
    # TODO
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["start_time"]
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"]


@pytest.mark.syncgateway
@pytest.mark.attachment_cleanup
@pytest.mark.parametrize("delete_doc_type", [
    "purge",
    "expire"
])
def test_upgrade_purge_expire_attachments(params_from_base_test_setup, delete_doc_type):
    """
    :param params_from_base_test_setup:
    :return:
    1. Start the SG and CB
    2. Create docs with attachments on SG and CB (xattrs)
    3. Verify the documents on the SG
    4. Purge all the documents on the SG
    5. Verify purged documents on the SG
    6. Verify the deleted attachments in the bucket
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
        pytest.skip('This test cannot run with sg version below 3.0.0')
    sg_conf_name = "sync_gateway_default"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    cbs_cluster.reset(sg_config_path=temp_sg_config)
    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_previous_version, True)
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, remote_db, username, password=password, channels=sg_channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, remote_db, username)
    session = cookie, session_id
    if delete_doc_type == "expire":
        added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com", channels=sg_channels,
                                       auth=session, attachments_generator=attachment.generate_5_png_100_100, expiry=6)
        added_doc2 = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com-1",
                                        channels=sg_channels, auth=session,
                                        attachments_generator=attachment.generate_5_png_100_100, expiry=6)
    else:
        added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com",
                                       channels=sg_channels, auth=session,
                                       attachments_generator=attachment.generate_5_png_100_100)
        added_doc2 = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com-1",
                                        channels=sg_channels, auth=session,
                                        attachments_generator=attachment.generate_5_png_100_100)

    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_version, True)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=remote_db, auth=session, include_docs=True)
    attachments = {}
    duplicate_attachments = attachment.load_from_data_dir(["sample_text.txt"])
    for att in duplicate_attachments:
        attachments[att.name] = {"data": att.data}
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com-1_" + str(5), number_updates=1,
                         update_attachment=attachments)

    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com-1_" + str(6), number_updates=1,
                         update_attachment=attachments)
    if delete_doc_type == "purge":
        sg_client.purge_docs(url=sg_admin_url, db=remote_db, docs=sg_docs["rows"])
    else:
        time.sleep(5)

    added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=10, id_prefix="att_com", channels=sg_channels,
                                   auth=session, attachments_generator=attachment.generate_5_png_100_100)

    # 3 . Upgrade SGW to lithium and have Automatic upgrade
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf,
                                cluster_conf)

    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com_" + str(6), number_updates=1,
                         update_attachment=attachments)

    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    sg_client.compact_attachments(sg_admin_url, remote_db, "stop")
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    status = sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"]
    if status == "stopping" or status == "running":
        sg_client.compact_attachments(sg_admin_url, remote_db, "progress")
        time.sleep(5)
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"] == "4956", "compaction count not matching"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["last_error"] == "", "Error found while running the compaction process"
    # TODO
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["start_time"]
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"]


@pytest.mark.syncgateway
@pytest.mark.attachment_cleanup
def test_upgrade_legacy_attachments(params_from_base_test_setup):
    """
        1.Setup a node with SG version 2.8.0 installed.
        2. Create 3 different documents with 3 different inline attachments.
        doc1 -> att1
        doc2 -> att2
        doc3 -> att3
        3. Create 4 more documents sharing the same attachment.
        doc4 -> att4
        doc5 -> att4
        doc6 -> att4
        doc7 -> att4
        4. Stop SG, upgrade to the Lithium version 3.0.0, and start SG.
        5. Update doc1 by removing att1 and verify that the att1 is still persisted in the bucket.
        6. Delete doc2  and verify that the att2 is still persisted in the bucket.
        7. Purge doc3 and verify that the att3 is still persisted in the bucket.
        8. Update doc4 by removing att4 and verify that the att4 is still persisted in the bucket.
        9. Delete doc5  and verify that the att4 is still persisted in the bucket.
        10. Purge doc6 and verify that the att4 is still persisted in the bucket.
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
        pytest.skip('This test cannot run with sg version below 3.0.0')
    sg_conf_name = "sync_gateway_default"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cbs_cluster = Cluster(config=cluster_conf)
    sg1 = cbs_cluster.sync_gateways[0]
    # temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    cbs_cluster.reset(sg_config_path=temp_sg_config)
    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_previous_version, True)

    # 1. Setup a node with SG version 2.8.0 installed.
    sg_obj.install_sync_gateway(cluster_conf, sync_gateway_previous_version, temp_sg_config)
    cluster_util = ClusterKeywords(cluster_conf)
    topology = cluster_util.get_cluster_topology(cluster_conf)
    sync_gateways = topology["sync_gateways"]
    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, remote_db, username, password=password, channels=sg_channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, remote_db, username)
    session = cookie, session_id

    # 2. Create 3 different documents with 3 different inline attachments.
    added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=3, id_prefix="att_com-1",
                                   channels=sg_channels,
                                   auth=session, attachments_generator=attachment.generate_png_1_1)

    # 3. Create 4 more documents sharing the same attachment.
    added_doc = sg_client.add_docs(url=sg_url, db=remote_db, number=4, id_prefix="att_same",
                                   channels=sg_channels, auth=session)

    attachments = {}
    duplicate_attachments = attachment.load_from_data_dir(["sample_text.txt"])
    for att in duplicate_attachments:
        attachments[att.name] = {"data": att.data}
    # sharing the same attachment
    for i in range(4):
        sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_same_" + str(i), number_updates=1,
                             update_attachment=attachments)
    persist_cluster_config_environment_prop(cluster_conf, 'sync_gateway_version', sync_gateway_version, True)

    # 4. Stop SG, upgrade to the Lithium version 3.0.0, and start SG.
    sg_obj.upgrade_sync_gateway(sync_gateways, sync_gateway_previous_version, sync_gateway_version, sg_conf,
                                cluster_conf)

    # Get all attachment names

    set_one_attachment_name = []
    set_one_attachment_ids = []

    for i in range(3):
        raw_doc = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc="att_com-1_" + str(i))
        att_name = list(raw_doc["_attachments"].keys())[0]
        att_name = att_name.replace('/', '%2F')
        set_one_attachment_name.append(att_name)
        attachment_raw = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc="att_com-1_" + str(i),
                                                              attachment=att_name)
        set_one_attachment_ids.append(attachment_raw['key'])

    set_two_attachment_name = []
    set_two_attachment_ids = []
    for i in range(4):
        raw_doc = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc="att_same_" + str(i))
        att_name = list(raw_doc["_attachments"].keys())[0]
        att_name = att_name.replace('/', '%2F')
        set_two_attachment_name.append(att_name)
        attachment_raw = sg_client.get_attachment_by_document(sg_admin_url, db=remote_db, doc="att_same_" + str(i),
                                                              attachment=att_name)
        set_two_attachment_ids.append(attachment_raw['key'])

    cluster_topology = params_from_base_test_setup['cluster_topology']
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    if ssl_enabled:
        connection_url = "couchbases://{}?ssl=no_verify".format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    bucket_name = 'data-bucket'
    sdk_client = get_cluster(connection_url, bucket_name)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=remote_db, auth=session, include_docs=True)
    # 5. Update doc1 by removing att1 and verify that the att1 is still persisted in the bucket.
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_com-1_0", number_updates=1, update_attachment={})

    #  6. Delete doc2  and verify that the att is still persisted in the bucket.
    doc_id = "att_com-1_1"
    latest_rev = sg_client.get_latest_rev(sg_admin_url, remote_db, doc_id, session)
    sg_client.delete_doc(url=sg_admin_url, db=remote_db, doc_id=doc_id, rev=latest_rev, auth=session)

    # 7. Purge doc3 and verify that the att3 is still persisted in the bucket.
    sg_client.purge_docs(url=sg_admin_url, db=remote_db, docs=[sg_docs["rows"][2]])

    # Update doc4 by removing att4 and verify that the att4 is still persisted in the bucket.
    sg_client.update_doc(url=sg_admin_url, db=remote_db, doc_id="att_same_0", number_updates=1, update_attachment={})
    # 9. Delete doc5  and verify that the att4 is still persisted in the bucket.
    latest_rev = sg_client.get_latest_rev(sg_admin_url, remote_db, "att_same_1", session)
    sg_client.delete_doc(url=sg_admin_url, db=remote_db, doc_id="att_same_1", rev=latest_rev, auth=session)
    # 10. Purge doc6 and verify that the att4 is still persisted in the bucket.
    sg_client.purge_docs(url=sg_admin_url, db=remote_db, docs=[sg_docs["rows"][4]])

    # # Verify all attachments are still present
    for att_id in set_one_attachment_ids:
        sdk_client.get(att_id)

    for att_id in set_two_attachment_ids:
        sdk_client.get(att_id)

    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    sg_client.compact_attachments(sg_admin_url, remote_db, "stop")
    sg_client.compact_attachments(sg_admin_url, remote_db, "start")
    status = sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"]
    if status == "stopping" or status == "running":
        sg_client.compact_attachments(sg_admin_url, remote_db, "progress")
        time.sleep(5)
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["status"] == "stopped"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"] == "4", "compaction count not matching"
    assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["last_error"] == "", "Error found while running the compaction process"
    # TODO
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["start_time"]
    #  assert sg_client.compact_attachments(sg_admin_url, remote_db, "status")["marked_attachments"]

