from datetime import datetime
import os
import pytest
import random
import time
from concurrent.futures import ThreadPoolExecutor
from couchbase.bucket import Bucket
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway
from keywords.utils import add_new_fields_to_doc, host_for_url, log_info, add_additional_new_field_to_doc
from libraries.testkit.cluster import Cluster
from libraries.testkit import cluster

from requests.exceptions import HTTPError

DB1 = "sg_db1"
DB2 = "sg_db2"


def redeploy_sync_gateway(cluster_config, mode, sync_gateway_version):
    sgwgateway = SyncGateway()
    sg_conf_name = "listener_tests/multiple_sync_gateways"

    c_cluster = cluster.Cluster(config=cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c_cluster.reset(sg_config_path=sg_config)

    sg1 = c_cluster.sync_gateways[0]
    sg2 = c_cluster.sync_gateways[1]

    sgw_cluster1_conf_name = sync_gateway_config_path_for_mode('listener_tests/sg_replicate_sgw_cluster1', mode)
    sgw_cluster2_conf_name = sync_gateway_config_path_for_mode('listener_tests/sg_replicate_sgw_cluster2', mode)

    sg_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_conf_name)
    sg_cluster2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_conf_name)
    sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sg_cluster1_config_path, url=sg1.ip,
                                            sync_gateway_version=sync_gateway_version, enable_import=True)

    sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sg_cluster2_config_path, url=sg2.ip,
                                            sync_gateway_version=sync_gateway_version, enable_import=True)

    return sg1, sg2


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("auto_purge_setting", [
    pytest.param("enabled"),
    pytest.param("default"),
    pytest.param("disabled")
])
def test_auto_purge_setting_impact(params_from_base_test_setup, auto_purge_setting):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #1
        1. on passive SGW, create docs:
                doc_A belongs to channel A only,
                doc_AnB belongs to channel A and channel B
        2. start a pull continous replication on active SGW with auto_purge_setting parameter
        3. verify active SGW have pulled the doc_A and doc_AnB
        4. revoke the user access to channel A
        5. verify expected doc auto purge result on active SGW
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs: doc_A belongs to channel A only, doc_AnB belongs to channel A and channel B
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a pull continous replication sg1 <- sg2 with auto_purge_setting parameter
    if auto_purge_setting == "enabled":
        replicator2_id = sg1.start_replication2(
            local_db=DB1,
            remote_url=sg2.url,
            remote_db=DB2,
            remote_user=sg2_username,
            remote_password=password,
            direction="pull",
            continuous=True,
            purge_on_removal=True
        )
    elif auto_purge_setting == "disabled":
        replicator2_id = sg1.start_replication2(
            local_db=DB1,
            remote_url=sg2.url,
            remote_db=DB2,
            remote_user=sg2_username,
            remote_password=password,
            direction="pull",
            continuous=True,
            purge_on_removal=False
        )
    else:
        replicator2_id = sg1.start_replication2(
            local_db=DB1,
            remote_url=sg2.url,
            remote_db=DB2,
            remote_user=sg2_username,
            remote_password=password,
            direction="pull",
            continuous=True
        )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 3. verify active SGW have pulled the doc_A and doc_AnB
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 5. verify expected doc auto purge result on active SGW
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    if auto_purge_setting == "enabled":
        assert "sg2_A_0" not in sg1_doc_ids
        assert "sg2_AnB_0" in sg1_doc_ids
    else:
        for sg2_doc_id in sg2_doc_ids:
            assert sg2_doc_id in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("require_checkpoint_reset", [
    pytest.param(True),
    pytest.param(False)
])
def test_existing_replication_enabling_auto_purge(params_from_base_test_setup, require_checkpoint_reset):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #2 - 1
        1. on passive SGW, create docs in channel A, B, and C
        2. on active SGW, start a continous pull replication with default auto purge config (disabled)
        3. verify active SGW have all docs pulled
        4. remove the user from channel A, w/o additional replication activity by adding a doc in channel B
        5. verify docs belong to channel A not purged and remain on active SGW
        6. on active SGW, stop the replication, enable auto purge config, then start the replication, w/o reset checkpoint
        7. verify docs in channel A are purged, docs in other channels are not impacted
        8. remove the user from channel B
        9. verify active SGW docs in channel A and B are all purged, only docs in channel C exist
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs in channel A, B, and C
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=7, id_prefix="sg2_B", channels=["B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=5, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. on active SGW, start a continous pull replication with default auto purge config (disabled)
    replicator2_id_1 = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. remove the user from channel A, w/o additional replication activity by adding a doc in channel B
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)

    if require_checkpoint_reset:
        sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_BB", channels=["B"])
        sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)

    # 5. verify docs belong to channel A not purged and remain on active SGW
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 6. on active SGW, stop the replication, enable auto purge config, then start the replication, w/o reset checkpoint
    sg1.modify_replication2_status(replicator2_id_1, DB1, "stop")
    time.sleep(2)

    sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True,
        replication_id=replicator2_id_1
    )
    sg1.modify_replication2_status(replicator2_id_1, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)

    if require_checkpoint_reset:
        sg1.modify_replication2_status(replicator2_id_1, DB1, "reset")
        sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)

    # 7. verify docs in channel A are purged, docs in other channels are not impacted
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for doc_id in sg1_doc_ids:
        assert not doc_id.startswith("sg2_A")
        assert (doc_id.startswith("sg2_B") or doc_id.startswith("sg2_C"))

    # 8. remove the user from channel B
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=3000)

    # 9. verify active SGW docs in channel A and B are all purged, only docs in channel C exist
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]

    assert len(sg1_doc_ids) == 5
    for doc_id in sg1_doc_ids:
        assert not doc_id.startswith("sg2_A")
        assert not doc_id.startswith("sg2_B")

    sg1.stop_replication2_by_id(replicator2_id_1, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_new_replication_enabling_auto_purge(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #2 - 2
        1. on passive SGW, create docs in channel A and channel B
        2. on active SGW, start a continous pull replication with default auto purge config (disabled)
        3. verify active SGW have all docs pulled
        4. remove the user from channel A
        5. verify docs in channel A are not purged and remain on active SGW
        6. on active SGW, delete the replication and start another new pull replication with auto purge config enabled
        7. verify docs in channel A get purged
        8. remove the user from channel B
        9. verify active SGW docs in channel B also get purged
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs in channel A and channel B
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=7, id_prefix="sg2_B", channels=["B"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. on active SGW, start a continous pull replication with default auto purge config (disabled)
    replicator2_id_1 = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True
    )

    # 3. verify active SGW have all docs pulled
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=6000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. remove the user from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_1, read_flag=True, max_times=3000)

    # 5. verify docs in channel A are not purged and remain on active SGW
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 6. on active SGW, delete the replication and start another new pull replication with auto purge config enabled
    sg1.stop_replication2_by_id(replicator2_id_1, DB1)
    replicator2_id_2 = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, read_flag=True, max_times=3000)

    # 7. verify docs in channel A get purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for doc_id in sg1_doc_ids:
        assert not doc_id.startswith("sg2_A")

    # 8. remove the user from channel B
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, read_flag=True, max_times=3000)

    # 9. verify active SGW docs in channel B also get purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert len(sg1_doc_ids) == 0

    sg1.stop_replication2_by_id(replicator2_id_2, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_disable_auto_purge_no_impact_purged_docs(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #2 - 3
        1. on passive SGW, create doc_A_* belongs to channel A, doc_B_* belongs to channel B
        2. on active SGW, start a continous pull replication with auto purge enabled
        3. verify active SGW have pulled doc_A_* and doc_B_*
        4. remove the user from channel A, wait replication finishes operation and turns idle
        5. verify doc_A_* purged on active SGW
        6. on active SGW, pause the replication, disable the replication auto purge config, then start the replication
        7. verify doc_A_* not replicated back after the replication auto purge config update
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create doc_A_* belongs to channel A, doc_B_* belongs to channel B
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=7, id_prefix="sg2_B", channels=["B"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. on active SGW, start a continous pull replication with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )

    # 3. verify active SGW have pulled doc_A_* and doc_B_*
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. remove the user from channel A, wait replication finishes operation and turns idle
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 5. verify doc_A_* purged on active SGW
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for doc_id in sg1_doc_ids:
        assert not doc_id.startswith("sg2_A")
        assert doc_id.startswith("sg2_B")

    # 6. on active SGW, pause the replication, disable the replication auto purge config, then start the replication
    sg1.modify_replication2_status(replicator2_id, DB1, "stop")
    time.sleep(3)
    sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=False,
        replication_id=replicator2_id,
        channels=channels
    )
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 7. verify doc_A_* not replicated back after the replication auto purge config update
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for doc_id in sg1_doc_ids:
        assert not doc_id.startswith("sg2_A")
        assert doc_id.startswith("sg2_B")

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.sanity
@pytest.mark.syncgateway
def test_user_lost_channel_access_pull(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #3
        1. on passive SGW, create docs:
            - doc_A belongs to channel A only
            - doc_AnB belongs to channel A and channel B
            - doc_C belongs to channel C only
        2. start a pull replication on active SGW with auto purge enabled
        3. verify active SGW pulled the doc_A, doc_AnB, and doc_C
        4. revoke the user access to channel A
        5. verify doc_A auto purged, doc_AnB and doc_C have no impact
        6. update doc_C three times on active SGW
        7. revoke the user access to channel C
        8. verify doc_C auto purged
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    #       - doc_A belongs to channel A only
    #       - doc_AnB belongs to channel A and channel B
    #       - doc_C belongs to channel C only
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a pull replication on active SGW with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 3. verify active SGW pulled the doc_A, doc_AnB, and doc_C
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. revoke the user access to channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 5. verify doc_A auto purged, doc_AnB and doc_C have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 6. update doc_C three times on active SGW
    sg_client.update_doc(url=sg1.url, db=DB1, doc_id="sg2_C_0",
                         number_updates=3, auth=auth_session1,
                         property_updater=add_new_fields_to_doc)

    # 7. revoke the user access to channel C
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 8. verify doc_C auto purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_user_lost_channel_access_push_only(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #6
        1. on passive SGW, create docs:
            - doc_A belongs to channel A only
            - doc_AnB belongs to channel A and channel B
            - doc_C belongs to channel C only
        2. start a one-time pull replication sg1 <- sg2 with default config
        3. verify active SGW pulled the doc_A, doc_AnB, and doc_C
        4. update the replication to push and enable auto purge
        5. revoke user access from channel A
        6. verify docs are not impacted
        7. revoke user access from channel C
        8. update doc_C three times
        9. verify docs are not impacted and verify pushing modified docs got rejected
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    #       - doc_A belongs to channel A only
    #       - doc_AnB belongs to channel A and channel B
    #       - doc_C belongs to channel C only
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a one-time pull replication sg1 <- sg2 with default config
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=False
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 3. verify active SGW pulled the doc_A, doc_AnB, and doc_C
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. update the replication to push and enable auto purge
    sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        replication_id=replicator2_id,
        direction="push",
        continuous=True,
        purge_on_removal=True
    )
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    # 5. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(3)

    # 6. verify docs are not impacted
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, max_times=3000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 7. revoke user access from channel C
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(3)

    # 8. update doc_C three times
    doc_c_id = "sg2_C_0"
    sg_client.update_doc(url=sg1.url, db=DB1, doc_id=doc_c_id,
                         number_updates=3, auth=auth_session1,
                         property_updater=add_new_fields_to_doc)

    # 9. verify docs are not impacted and verify pushing modified docs got rejected
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, max_times=3000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    with pytest.raises(HTTPError) as ex:
        sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=doc_c_id)
    assert str(ex.value).startswith("403 Client Error: Forbidden for url:")

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_user_lost_channel_access_push_and_pull(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #9
        1. on passive SGW, create docs:
            - doc_A belongs to channel A only
            - doc_AnB belongs to channel A and channel B
            - doc_C belongs to channel C only
        2. start a push_pull replication sg1 <- sg2 with auto purge enabled
        3. verify active SGW have all docs pulled
        4. revoke user access from channel A
        5. verify docs in channel A are purged, other docs are not impacted
        6. pause the replication, update doc_c three times
        7. revoke user access from channel C, then turn the replication back online
        8. verify docs in channel C are purged
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    #       - doc_A belongs to channel A only
    #       - doc_AnB belongs to channel A and channel B
    #       - doc_C belongs to channel C only
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a push_pull replication sg1 <- sg2 with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pushAndPull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(3)

    # 5. verify docs in channel A are purged, other docs are not impacted
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 6. pause the replication, update doc_c three times
    sg1.modify_replication2_status(replicator2_id, DB1, "stop")
    doc3_id = "sg2_C_0"
    sg_client.update_doc(url=sg1.url, db=DB1, doc_id=doc3_id,
                         number_updates=3, auth=auth_session1,
                         property_updater=add_new_fields_to_doc)

    # 7. revoke user access from channel C, then turn the replication back online
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B"])
    time.sleep(3)
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, write_flag=True, max_times=3000)

    # 8. verify docs in channel C are purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("replication_direction", [
    pytest.param("pull"),
    pytest.param("pushAndPull")
])
def test_user_removed_from_role_by_direction(params_from_base_test_setup, replication_direction):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #4 & #10
        1. create roles and user:
            - role1 has access to channel A and B
            - role2 has access to channel B and C
            - user belongs to R1 and R2, can also access to channel C
        2. create docs:
            - doc_A belongs to channel A only
            - doc_B belongs to channel B only
            - doc_AnB belongs to channel A and B
            - doc_AnC belongs to channel A and C
            - doc_C belongs to channel C
        3. start a replication sg1 <- sg2 with with auto purge enabled
        4. verify active SGW have all docs pulled
        5. on SGW remove the user from role1
        6. verify docs in channel A are auto purged, others have no impact
        7. on SGW remove the user from role2
        8. verify docs in channel A or B are auto-purged, others have no impact
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # 1. create roles and users
    role1 = "R1"
    role2 = "R2"
    roles = [role1, role2]
    role1_channels = ["A", "B"]
    role2_channels = ["B", "C"]
    other_channels = ["C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role1, channels=role1_channels)
    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role2, channels=role2_channels)

    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role1, channels=role1_channels)
    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role2, channels=role2_channels)

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=other_channels, roles=roles)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=other_channels, roles=roles)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 2. create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_B", channels=["B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnC", channels=["A", "C"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    # get docs on passive SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 3. start a replication sg1 <- sg2 with with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction=replication_direction,
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 4. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 5. on SGW remove the user from role1
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=other_channels, roles=[role2])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 6. verify docs in channel A are auto purged, others have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 7. on SGW remove the user from role2
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=other_channels, roles=[])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 8. verify docs in channel A or B are auto-purged, others have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_B_0" not in sg1_doc_ids
    assert "sg2_AnB_0" not in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_user_removed_from_role_push_only(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #7
        1. create roles and user:
            - role R1 has access to channel A and B
            - role R2 has access to channel B and C
            - user belongs to R1 and R2, can also access to channel C
        2. create docs:
            - doc_A belongs to channel A only
            - doc_B belongs to channel B only
            - doc_AnB belongs to channel A and B
            - doc_AnC belongs to channel A and C
            - doc_C belongs to channel C
        3. start a pull replication sg1 <- sg2 with with default auto purge config
        4. verify active SGW have all docs pulled
        5. update the replication direction to push and purge_on_removal enabled
        6. on SGW remove the user from role1
        7. verify docs have no impact
        8. on SGW remove the user from role2
        9. verify docs have no impact
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # 1. create roles and users
    role1 = "R1"
    role2 = "R2"
    roles = [role1, role2]
    role1_channels = ["A", "B"]
    role2_channels = ["B", "C"]
    other_channels = ["C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role1, channels=role1_channels)
    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role2, channels=role2_channels)

    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role1, channels=role1_channels)
    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role2, channels=role2_channels)

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=other_channels, roles=roles)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=other_channels, roles=roles)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 2. create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_B", channels=["B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnC", channels=["A", "C"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 3. start a pull replication sg1 <- sg2 with with default auto purge config
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=False
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 4. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 5. update the replication direction to push and purge_on_removal enabled
    sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        replication_id=replicator2_id,
        direction="push",
        continuous=True,
        purge_on_removal=True
    )
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 6. on SGW remove the user from role1
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=other_channels, roles=[role2])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 7. verify docs have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]

    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 8. on SGW remove the user from role2
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=other_channels, roles=[])
    time.sleep(2)

    # 9. verify docs have no impact
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]

    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("replication_direction", [
    pytest.param("pull"),
    pytest.param("pushAndPull")
])
def test_user_role_revoked_channel_access_by_direction(params_from_base_test_setup, replication_direction):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #5 & #11
        1. create role and user:
            - role R access to channel A, B and D
            - user assigned to role R and channel C
        2. create docs:
            - doc_A belongs to channel A only
            - doc_B belongs to channel B only
            - doc_AnB belongs to channel A and B
            - doc_AnC belongs to channel A and C
            - doc_C belongs to channel C
        3. start a replication sg1 <- sg2 with with auto purge enabled
        4. verify active SGW have all docs pulled
        5. role R lost access to channel A
        6. verify docs in channel A are auto purged, others have no impact
        7. role R lost access to channel B
        8. verify docs in channel A or channel B are auto-purged, others have  no impact
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # 1. create roles and users
    role = "R"
    roles = [role]
    role_channels = ["A", "B", "D"]
    other_channels = ["C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role, channels=role_channels)
    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=role_channels)

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=other_channels, roles=roles)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=other_channels, roles=roles)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 2. create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_B", channels=["B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnC", channels=["A", "C"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    # get docs on passive SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 3. start a replication sg1 <- sg2 with with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction=replication_direction,
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 4. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 5. role R lost access to channel A
    sg_client.update_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=["B", "D"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 6. verify docs in channel A are auto purged, others have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 7. role R lost access to channel B
    sg_client.update_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=["D"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 8. verify docs in channel A or channel B are auto-purged, others have  no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_B_0" not in sg1_doc_ids
    assert "sg2_AnB_0" not in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_user_role_revoked_channel_access_push_only(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #8
        1. create role and user:
            - role R access to channel A, B and D
            - user assigned to role R and channel C
        2. create docs:
            - doc_A belongs to channel A only
            - doc_B belongs to channel B only
            - doc_AnB belongs to channel A and B
            - doc_AnC belongs to channel A and C
            - doc_C belongs to channel C
        3. start a pull replication sg1 <- sg2 with default auto purge config
        4. verify active SGW have all docs pulled
        5. update the replication direction to push and auto purge enabled
        6. role R lost access to channel A
        7. verify docs have no impact
        8. role R lost access to channel B
        9. verify docs have no impact
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # 1. create roles and users
    role = "R"
    roles = [role]
    role_channels = ["A", "B", "D"]
    other_channels = ["C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_role(url=sg1.admin.admin_url, db=DB1, name=role, channels=role_channels)
    sg_client.create_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=role_channels)

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=other_channels, roles=roles)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=other_channels, roles=roles)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 2. create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_B", channels=["B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnC", channels=["A", "C"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    # get docs on passive SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 3. start a pull replication sg1 <- sg2 with default auto purge config
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull"
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 4. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 5. update the replication direction to push and auto purge enabled
    sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        replication_id=replicator2_id,
        continuous=True,
        direction="push",
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, max_times=3000)

    # 6. role R lost access to channel A
    sg_client.update_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=["B"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, max_times=3000)

    # 7. verify docs have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 8. role R lost access to channel B
    sg_client.update_role(url=sg2.admin.admin_url, db=DB2, name=role, channels=[])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, max_times=3000)

    # 9. verify docs have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_B_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_AnC_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.sanity
@pytest.mark.syncgateway
def test_user_reassign_to_channel_pull(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #13
        1. on passive SGW, create docs:
            - doc_A belongs to channel A only
            - doc_AnB belongs to channel A and B
            - doc_C belongs to channel C
        2. start a pull replication sg1 <- sg2 with with auto purge enabled
        3. verify active SGW have all docs pulled
        4. revoke user access from channel A
        5. verify docs in channel A get auto purged, docs in other channels have no impact
        6. reassign user access to channel A, but revoke access to channel C
        7. verify docs in channel A previously auto purged are now back, docs in channel C are purged now
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a pull replication sg1 <- sg2 with with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 5. verify docs in channel A get auto purged, docs in other channels have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 6. reassign user access to channel A, but revoke access to channel C
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["A", "B"])
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 7. verify docs in channel A previously auto purged are now back, docs in channel C are purged now
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.oscertify
def test_user_reassign_to_channel_push_only(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #14
        1. on passive SGW, create docs:
            - doc_A in channel A only
            - doc_AnB in channel A and channel B
            - doc_C in channel C only
        2. start a one-time pull replication sg1 <- sg2 with default config
        3. verify active SGW have all docs pulled
        4. update the replication direction to push and enable auto purge
        5. revoke user access from channel A
        6. verify docs have no impact
        7. on active SGW, add a new doc to channel A, update doc_A and verify doc_A update doesn't get pushed
        8. reassign user access to channel A, and verify docs not impacted
        9. on active SGW, add another doc, update doc_A again, verify the docs pushed after user reassigned to channel access
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a one-time pull replication sg1 <- sg2 with default config
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=False
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids
    sg1.stop_replication2_by_id(replicator2_id, DB1)

    # 4. update the replication direction to push and enable auto purge
    replicator2_id_2 = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="push",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, write_flag=True, read_flag=True, max_times=3000)

    # 5. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, write_flag=True, read_flag=True, max_times=3000)

    # 6. verify docs have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 7. on active SGW, add a new doc to channel A, update doc_A and verify doc_A update doesn't get pushed
    sg_client.add_docs(url=sg1.url, db=DB1, number=1, id_prefix="doc_before_reassign", channels=["A"], auth=auth_session1)

    updated_doc_id = "sg2_A_0"
    sg_client.update_doc(url=sg1.url, db=DB1, doc_id=updated_doc_id,
                         number_updates=3, auth=auth_session1,
                         property_updater=add_new_fields_to_doc)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, write_flag=True, read_flag=True, max_times=3000)

    with pytest.raises(HTTPError) as ex:
        updated_doc_remote = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=updated_doc_id)
    assert str(ex.value).startswith("403 Client Error: Forbidden for url:")

    # 8. reassign user access to channel A, and verify docs not impacted
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["A", "B", "C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, write_flag=True, read_flag=True, max_times=3000)

    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 9. on active SGW, add another doc, update doc_A again, verify the docs pushed after user reassigned to channel access
    sg_client.add_docs(url=sg1.url, db=DB1, number=1, id_prefix="doc_after_reassign", channels=["A"], auth=auth_session1)
    sg_client.update_doc(url=sg1.url, db=DB1, doc_id=updated_doc_id,
                         number_updates=1, auth=auth_session1,
                         property_updater=add_additional_new_field_to_doc)

    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id_2, write_flag=True, read_flag=True, max_times=3000)

    updated_doc_local = sg_client.get_doc(url=sg1.url, db=DB1, auth=auth_session1, doc_id=updated_doc_id)
    updated_doc_remote = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=updated_doc_id)
    assert updated_doc_local == updated_doc_remote, "doc should be pushed after user reasigned to channel access"

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]
    assert "doc_before_reassign_0" in sg2_doc_ids
    assert "doc_after_reassign_0" in sg2_doc_ids

    sg1.stop_replication2_by_id(replicator2_id_2, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_user_reassign_to_channel_push_pull(params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #15
        1. on passive SGW, create docs:
            - doc_A belongs to channel A only
            - doc_AnB belongs to channel A and B
            - doc_C belongs to channel C
        2. start a push_pull replication sg1 <- sg2 with auto purge enabled config
        3. verify active SGW have all docs pulled
        4. revoke user access from channel A
        5. verify docs have no impact
        6. add a new doc on active SGW and verify this doc didn't get pushed to the passive SGW
        7. reassign user access to channel A and verify docs on active SGW
        8. verify the new doc gets replicated after user reassign channel access
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B", "C"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs:
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_C", channels=["C"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a push_pull replication sg1 <- sg2 with auto purge enabled config
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pushAndPull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    # 5. verify docs have no impact
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" not in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 6. add a new doc on active SGW and verify this doc didn't get pushed to the passive SGW
    sg1_doc_A = sg_client.add_docs(url=sg1.admin.admin_url, db=DB1, number=1, id_prefix="sg1_A", channels=["A"])
    new_doc_id = sg1_doc_A[0]["id"]
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    with pytest.raises(HTTPError) as ex:
        new_doc_remote = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=new_doc_id)
    assert str(ex.value).startswith("403 Client Error: Forbidden for url:")

    # 7. reassign user access to channel A and verify docs on active SGW
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["A", "B", "C"])
    time.sleep(3)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, write_flag=True, read_flag=True, max_times=3000)

    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert "sg2_A_0" in sg1_doc_ids
    assert "sg2_AnB_0" in sg1_doc_ids
    assert "sg2_C_0" in sg1_doc_ids

    # 8. verify the new doc gets replicated after user reassign channel access
    new_doc_local = sg_client.get_doc(url=sg1.url, db=DB1, auth=auth_session1, doc_id=new_doc_id)
    new_doc_remote = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=new_doc_id)
    assert new_doc_local == new_doc_remote, "doc should be replicated after user reassign channel access"


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("with_local_update", [
    pytest.param(False),
    pytest.param(True)
])
def test_auto_purge_for_tombstone_docs(params_from_base_test_setup, with_local_update):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #16
        1. on passive SGW, create docs in channel A and B
        2. start a pull replication sg1 <- sg2 with with auto purge enabled
        3. verify active SGW have all docs pulled
        4. pause the replication, tombstone a doc on remote, w/o local update for the tombstoned doc
        5. revoke user access from channel A and resume the replication
        6. verify the tombstoned docs get auto purged
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs in channel A and B
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=1, id_prefix="sg2_B", channels=["B"])
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a pull replication sg1 <- sg2 with with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 3. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 4. pause the replication, tombstone a doc on remote, w/o local update for the tombstoned doc
    sg1.modify_replication2_status(replicator2_id, DB1, "stop")

    doc_id_1 = "sg2_A_2"
    doc = sg_client.get_doc(url=sg2.url, db=DB2, doc_id=doc_id_1, auth=auth_session2)
    sg_client.delete_doc(url=sg2.url, db=DB2, doc_id=doc_id_1, rev=doc['_rev'], auth=auth_session2)
    if with_local_update:
        sg_client.update_doc(url=sg1.url, db=DB1, doc_id=doc_id_1,
                             number_updates=3, auth=auth_session1,
                             property_updater=add_new_fields_to_doc)

    doc_id_2 = "sg2_A_9"
    doc = sg_client.get_doc(url=sg2.url, db=DB2, doc_id=doc_id_2, auth=auth_session2)
    sg_client.delete_doc(url=sg2.url, db=DB2, doc_id=doc_id_2, rev=doc['_rev'], auth=auth_session2)
    if with_local_update:
        sg_client.update_doc(url=sg1.url, db=DB1, doc_id=doc_id_2,
                             number_updates=3, auth=auth_session1,
                             property_updater=add_new_fields_to_doc)

    # 5. revoke user access from channel A and resume the replication
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(2)
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 6. verify the tombstoned docs get auto purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert doc_id_1 not in sg1_doc_ids
    assert doc_id_2 not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
@pytest.mark.parametrize("resurrect_type", [
    pytest.param("same_doc_body"),
    pytest.param("different_doc_body")
])
def test_resurrected_docs_by_sdk(params_from_base_test_setup, resurrect_type):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #17 & #18
        1. on passive SGW, create docs in channel A
        2. randomly pick a random doc and update the doc three times
        3. start a pull replication sg1 <- sg2 with with auto purge enabled
        4. verify active SGW have all docs pulled
        5. pause the replication, delete the doc on passive SGW then add back from sdk with same id
        6. verify doc created from sdk imported to SGW
        7. revoke user access from channel A
        8. start the pull replication again and verify the resurrected doc gets auto purged
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    if not xattrs_enabled:
        pytest.skip("This test only runs with xattrs enabled scenario")

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    cbs_host = host_for_url(cbs_url)
    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs in channel A
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)

    # 2. randomly pick a random doc and update the doc three times
    random_idx = random.randrange(1, 10)
    selected_doc = sg2_docs["rows"][random_idx]
    selected_doc_id = selected_doc["id"]
    selected_doc_body_at_rev_1 = selected_doc["doc"]

    sg_client.update_doc(url=sg2.url, db=DB2, doc_id=selected_doc_id,
                         number_updates=3, auth=auth_session2,
                         property_updater=add_new_fields_to_doc)

    # 3. start a pull replication sg1 <- sg2 with with auto purge enabled
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 4. verify active SGW have all docs pulled
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert selected_doc_id in sg1_doc_ids

    # 5. pause the replication, delete the doc on passive SGW then add back from sdk with same id
    sg1.modify_replication2_status(replicator2_id, DB1, "stop")
    time.sleep(3)

    selected_doc_rev_latest = sg_client.get_doc(url=sg2.url, db=DB2, doc_id=selected_doc_id, auth=auth_session2)
    sg_client.delete_doc(url=sg2.url, db=DB2, doc_id=selected_doc_id, rev=selected_doc_rev_latest['_rev'], auth=auth_session2)

    bucket_name = 'data-bucket-2'
    cbs_cluster = Cluster(config=cluster_config)
    if cbs_cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    def update_doc_body():
        return selected_doc_body_at_rev_1

    if resurrect_type == "same_doc_body":
        sdk_doc_body = document.create_doc(selected_doc_id, channels=['A'], prop_generator=update_doc_body)
        log_info('Adding doc via SDK with doc body {}'.format(sdk_doc_body))
    else:
        def update_props():
            return {
                'updates': 999,
                "sg_tracking_prop": 0,
                "sdk_tracking_prop": 0
            }
        sdk_doc_body = document.create_doc(selected_doc_id, prop_generator=update_props, channels=['A'])
        log_info('Adding doc via SDK with doc body {}'.format(sdk_doc_body))

    sdk_client.upsert(selected_doc_id, sdk_doc_body)
    time.sleep(2)  # give some time to replicate to SGW

    # 6. verify doc created from sdk imported to SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    resurrected_doc_body = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=selected_doc_id)
    assert compare_doc_body(sdk_doc_body, resurrected_doc_body)

    # 7. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"])
    time.sleep(2)

    # 8. start the pull replication again and verify the resurrected doc gets auto purged
    sg1.modify_replication2_status(replicator2_id, DB1, "start")
    time.sleep(2)
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert selected_doc_id not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.syncgateway
def test_concurrent_update_on_channel_revocation(params_from_base_test_setup):
    """
        @summary:
        test case #12
        1. on passive SGW, create docs
        2. start a pull replication sg1 <- sg2 with default auto purge config
        3. verify active SGW have pulled all docs
        4. start 2 threads, one create and push docs, another pull constantly,
        5.. verify docs not impacted on active SGW
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=5, id_prefix="sg2_AnB", channels=["A", "B"])
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=3, id_prefix="sg2_B", channels=["B"])

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]

    # 2. start a pull replication sg1 <- sg2 with default auto purge config, verify active SGW have pulled all docs
    replicator2_id = sg1.start_replication2(
        local_db=DB1,
        remote_url=sg2.url,
        remote_db=DB2,
        remote_user=sg2_username,
        remote_password=password,
        direction="pull",
        continuous=False
    )
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    for sg2_doc_id in sg2_doc_ids:
        assert sg2_doc_id in sg1_doc_ids

    # 3. start two threads, one create and push docs, another pull constantly
    repeats = 10
    sleep_period_in_sec = 5
    wait_time_in_sec = repeats * sleep_period_in_sec + 5

    with ThreadPoolExecutor(max_workers=2) as executor:
        create_and_push_task = executor.submit(
            create_and_push_docs,
            sg_client,
            sg1,
            sg2,
            DB1,
            DB2,
            sg2_username,
            password,
            repeats,
            sleep_period_in_sec)
        pulling_task = executor.submit(
            pull_docs_in_parallel,
            sg1,
            sg2,
            DB1,
            DB2,
            sg2_username,
            password,
            wait_time_in_sec)

        create_and_push_task.result()
        pulling_task.result()

    # 4. verify docs not impacted on active SGW
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]

    for sg1_doc_id in sg1_doc_ids:
        assert not sg1_doc_id.startswith("sg2_A_")
        assert sg1_doc_id.startswith("sg2_AnB") or sg1_doc_id.startswith("sg2_B") or sg1_doc_id.startswith("local_A_")

    for i in range(repeats):
        for j in range(3):
            if i > repeats / 2:
                # doc added after user lost access : doc remains on local, push gets rejected by remote
                assert "local_A_{}_{}".format(i, j) in sg1_doc_ids
            else:
                # doc added before user lost access, doc gets pushed to remote
                # another replication thread purge it on local when user lost access
                assert "local_A_{}_{}".format(i, j) not in sg1_doc_ids


def compare_doc_body(doc1, doc2):
    try:
        del doc1["_rev"]
    except KeyError:
        log_info("no _rev exists")
    try:
        del doc2["_rev"]
    except KeyError:
        log_info("no _rev exists")
    try:
        del doc1["_revisions"]
    except KeyError:
        log_info("no _revisions exists")
    try:
        del doc2["_revisions"]
    except KeyError:
        log_info("no _revisions exists")
    return doc1 == doc2


def create_and_push_docs(sg_client, local_sg, remote_sg, local_db, remote_db, remote_user, password, repeats, sleep_period):
    # this method makes repeat actions to create docs in local db and push to remote db
    sg1 = local_sg
    sg2 = remote_sg
    user_revoked = False
    revocation_mark = 0
    for i in range(repeats):
        if i > repeats / 2 and not user_revoked:
            # revoke user access from channel A
            sg_client.update_user(url=sg2.admin.admin_url, db=remote_db, name=remote_user, channels=["B"])
            time.sleep(5)
            user_revoked = True
            revocation_mark = i
        # add 3 docs each time
        sg_client.add_docs(url=sg1.admin.admin_url, db=local_db, number=3, id_prefix="local_A_{}".format(i), channels=["A"])
        sg1.start_replication2(
            local_db=local_db,
            remote_url=sg2.url,
            remote_db=remote_db,
            remote_user=remote_user,
            remote_password=password,
            direction="push",
            continuous=True
        )
        time.sleep(sleep_period)

    return revocation_mark


def pull_docs_in_parallel(local_sg, remote_sg, local_db, remote_db, remote_user, password, wait_time_in_sec):
    sg1 = local_sg
    sg2 = remote_sg
    start_time = datetime.now()
    repl_id = sg1.start_replication2(
        local_db=local_db,
        remote_url=sg2.url,
        remote_db=remote_db,
        remote_user=remote_user,
        remote_password=password,
        direction="pull",
        continuous=True,
        purge_on_removal=True
    )
    time.sleep(wait_time_in_sec)
    sg1.stop_replication2_by_id(repl_id, local_db)
    end_time = datetime.now()

    return (end_time - start_time).total_seconds()
