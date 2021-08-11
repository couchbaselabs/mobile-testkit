import pdb

from datetime import datetime
import random
import pytest
# import logging
import time
# from concurrent.futures import ThreadPoolExecutor
from couchbase.bucket import Bucket
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode, create_sync_gateways
from keywords.utils import add_new_fields_to_doc, host_for_url, log_info, add_additional_new_field_to_doc
from libraries.testkit.cluster import Cluster

# from requests.exceptions import HTTPError

DB1 = "db1"
DB2 = "db2"


@pytest.mark.listener
@pytest.mark.channel_revocation
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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
@pytest.mark.parametrize("with_local_update", [
    pytest.param(False),
    pytest.param(True)
])
def test_auto_purge_for_tombstone_docs(params_from_base_test_setup, with_local_update):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #13
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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    sg1.admin.wait_until_sgw_replication_done(DB1, replicator2_id, read_flag=True, max_times=3000)

    # 6. verify the tombstoned docs get auto purged
    sg1_docs = sg_client.get_all_docs(url=sg1.url, db=DB1, auth=auth_session1, include_docs=True)
    sg1_doc_ids = [doc["id"] for doc in sg1_docs["rows"]]
    assert doc_id_1 not in sg1_doc_ids
    assert doc_id_2 not in sg1_doc_ids

    sg1.stop_replication2_by_id(replicator2_id, DB1)


@pytest.mark.listener
@pytest.mark.channel_revocation
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
    config = sync_gateway_config_path_for_mode("sync_gateway_sg_replicate", mode)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

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
    cluster = Cluster(config=cluster_config)
    if cluster.ipv6:
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
        sdk_doc_body = document.create_doc(selected_doc_id, prop_generator=update_doc_body, channels=['A'])
        log_info('Adding doc via SDK with doc body {}'.format(sdk_doc_body))

    sdk_client.upsert(selected_doc_id, sdk_doc_body)
    time.sleep(2)  # give some time to replicate to SGW

    # 6. verify doc created from sdk imported to SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    resurrected_doc_body = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=selected_doc_id)
    pdb.set_trace()
    assert sdk_doc_body == resurrected_doc_body
    assert sdk_doc_body == sg2_docs[selected_doc_id]

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


def create_and_push_docs(sg_client, local_sg, remote_sg, local_db, remote_db, remote_user, password, repeats, sleep_period):
    # this method makes repeat actions to create docs in local db and push to remote db
    sg1 = local_sg
    sg2 = remote_sg
    user_revoked = False
    revocation_mark = 0
    for i in repeats:
        if i > repeats / 2 and not user_revoked:
            # revoke user access from channel A
            sg_client.update_user(url=sg2.admin.admin_url, db=remote_db, name=remote_user, channels=["B"])
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
            continuous=False
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
