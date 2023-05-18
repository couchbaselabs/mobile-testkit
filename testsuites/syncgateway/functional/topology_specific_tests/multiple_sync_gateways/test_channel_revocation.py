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
from keywords.constants import RBAC_FULL_ADMIN
from requests.auth import HTTPBasicAuth

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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    if not xattrs_enabled:
        pytest.skip("This test only runs with xattrs enabled scenario")

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    # if auth:
    #    sg1.admin.auth = HTTPBasicAuth(auth[0], auth[1])

    cbs_host = host_for_url(cbs_url)
    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels, auth=auth)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels, auth=auth)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username, auth=auth)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username, auth=auth)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs in channel A
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"], auth=auth)

    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)

    # 2. randomly pick a random doc and update the doc three times
    random_idx = random.randrange(1, 10)
    selected_doc = sg2_docs["rows"][random_idx]
    selected_doc_id = selected_doc["id"]
    selected_doc_body_at_rev_1 = selected_doc["doc"]
    del selected_doc_body_at_rev_1["_id"]
    del selected_doc_body_at_rev_1["_rev"]

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

    print("selected doc body at rev1 is  ", selected_doc_body_at_rev_1)
    if resurrect_type == "same_doc_body":
        sdk_doc_body = document.create_doc(selected_doc_id, channels=['A'], prop_generator=update_doc_body, non_sgw=True)
        log_info('Adding doc via SDK with doc body {}'.format(sdk_doc_body))
    else:
        def update_props():
            return {
                'updates': 999,
                "sg_tracking_prop": 0,
                "sdk_tracking_prop": 0
            }
        sdk_doc_body = document.create_doc(selected_doc_id, prop_generator=update_props, channels=['A'], non_sgw=True)
        log_info('Adding doc via SDK with doc body {}'.format(sdk_doc_body))

    sdk_client.upsert(selected_doc_id, sdk_doc_body)
    time.sleep(2)  # give some time to replicate to SGW

    # 6. verify doc created from sdk imported to SGW
    sg2_docs = sg_client.get_all_docs(url=sg2.url, db=DB2, auth=auth_session2, include_docs=True)
    resurrected_doc_body = sg_client.get_doc(url=sg2.url, db=DB2, auth=auth_session2, doc_id=selected_doc_id)
    assert compare_doc_body(sdk_doc_body, resurrected_doc_body)

    # 7. revoke user access from channel A
    sg_client.update_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, channels=["B", "C"], auth=auth)
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # prepare sync gateway environment
    sg1, sg2 = redeploy_sync_gateway(cluster_config, mode, sync_gateway_version)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    if auth:
        sg1.admin.auth = HTTPBasicAuth(auth[0], auth[1])

    sg_client = MobileRestClient()

    # create users, user sessions
    channels = ["A", "B"]
    sg1_username = "sg1_user"
    sg2_username = "sg2_user"
    password = "password"

    sg_client.create_user(url=sg1.admin.admin_url, db=DB1, name=sg1_username, password=password, channels=channels, auth=auth)
    sg_client.create_user(url=sg2.admin.admin_url, db=DB2, name=sg2_username, password=password, channels=channels, auth=auth)

    cookie1, session1 = sg_client.create_session(url=sg1.admin.admin_url, db=DB1, name=sg1_username, auth=auth)
    auth_session1 = cookie1, session1

    cookie2, session2 = sg_client.create_session(url=sg2.admin.admin_url, db=DB2, name=sg2_username, auth=auth)
    auth_session2 = cookie2, session2

    # 1. on passive SGW, create docs
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=10, id_prefix="sg2_A", channels=["A"], auth=auth)
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=5, id_prefix="sg2_AnB", channels=["A", "B"], auth=auth)
    sg_client.add_docs(url=sg2.admin.admin_url, db=DB2, number=3, id_prefix="sg2_B", channels=["B"], auth=auth)

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
            sleep_period_in_sec,
            auth)
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
    try:
        del doc1["_id"]
    except KeyError:
        log_info("no _id exists")
    try:
        del doc2["_id"]
    except KeyError:
        log_info("no _id exists")
    return doc1 == doc2


def create_and_push_docs(sg_client, local_sg, remote_sg, local_db, remote_db, remote_user, password, repeats, sleep_period, auth):
    # this method makes repeat actions to create docs in local db and push to remote db
    sg1 = local_sg
    sg2 = remote_sg
    user_revoked = False
    revocation_mark = 0
    for i in range(repeats):
        if i > repeats / 2 and not user_revoked:
            # revoke user access from channel A
            sg_client.update_user(url=sg2.admin.admin_url, db=remote_db, name=remote_user, channels=["B"], auth=auth)
            time.sleep(5)
            user_revoked = True
            revocation_mark = i
        # add 3 docs each time
        sg_client.add_docs(url=sg1.admin.admin_url, db=local_db, number=3, id_prefix="local_A_{}".format(i), channels=["A"], auth=auth)
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
