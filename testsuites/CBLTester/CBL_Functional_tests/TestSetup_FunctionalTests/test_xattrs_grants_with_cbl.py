import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode, replace_xattrs_sync_func_in_config
from keywords import document
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.couchbaseserver import get_sdk_client_with_bucket
import couchbase.subdocument as SD
from keywords.constants import RBAC_FULL_ADMIN


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("x509_cert_auth", [
    pytest.param(False, marks=pytest.mark.ce_sanity),
    pytest.param(True, marks=pytest.mark.sanity)
])
def test_xattrs_grant_automatic_imports(params_from_base_test_setup, x509_cert_auth):
    """
    @summary:
        "1. Set xattr key in config
         2. Write a sync function to assign user xattrs value as channel
         3. Create doc via SGW . Verify docs via SGW cannot be access by user
         4. Update doc with SDK to add user xattr
         5. Perform raw GET to ensure added user xattrs is visbible
         6. Verify doc is accessed by the user who has acess to the channel defined in user xattrs"
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sg_channel1_value = "abc"
    sg_channels1 = [sg_channel1_value]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'sg_xattrs_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    continuous = True
    num_of_docs = 10
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Set xattr key in config
    # 2. Write a sync function to assign user xattrs value as channel
    # Replace with sync function on sgw config to use user xattrs for channels
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)

    # Reset cluster to ensure no data in system
    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_config = temp_cluster_config
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1, auth=auth)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)
    # 3. Create doc via SGW
    sg_docs = document.create_docs('sg_xattrs', number=num_of_docs)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=auto_user)
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id, auth=auth)
    rev = raw_doc["_sync"]["rev"]

    # Verify docs via SGW cannot be access by user
    replicator = Replication(base_url)
    _, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, sg_channels1, sg_client, cbl_db, sg_blip_url, continuous=continuous, replication_type="push_pull", auth=auth)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 0, "cbl docs count is not 0"

    expvars = sg_client.get_expvars(sg_admin_url, auth=auth)
    import_count = expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]

    # 4. Update doc with SDK to add user xattr
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value, xattr=True, create_parents=True)])
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 1, "cbl docs count is not 1 after assigning the user xattrs to the channel"

    # 5. Verify  Import Count stats is 1
    expvars = sg_client.get_expvars(sg_admin_url, auth=auth)
    assert expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"] == import_count + 1, "import_count is not incremented"
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id, auth=auth)
    assert raw_doc["_meta"]["xattrs"][user_custom_channel] == sg_channel1_value, "raw doc did not get user xattrs value"
    assert rev == raw_doc["_sync"]["rev"], "rev did not get incremented "


@pytest.mark.channels
@pytest.mark.syncgateway
def test_reassigning_channels_using_user_xattrs(params_from_base_test_setup, setup_customized_teardown_test):
    """
    @summary:
        "1. Have a sync function to assign channel1 and verify doc can be accesssed user1 who has access to only channel1
        2.Add  user xattrs via sdk with channel1
        sync_xattrs: {
            channel1 : "xattrs_channel_one"
        }
        3. Verify doc can be accessed by user1, who has  access to only "xattrs_channel_one", but not by user2
        4. update the user xattrs via sdk from "xattrs_channel_one" to "xattrs_channel_two"
        5. Verify doc can be accessed by user2 who has  access to only "xattrs_channel_two"
        6. change channel to new channel(channel2), verify doc can be accessed only in new channel
        7. verify user1 cannot access the doc
        cover row #9, #38, #39
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    delta_sync_enabled = params_from_base_test_setup["delta_sync_enabled"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sg_channel1_value1 = "xattrs_channel_one"
    sg_channel1_value2 = "xattrs_channel_two"
    sg_channels_1 = [sg_channel1_value1]
    sg_channels_2 = [sg_channel1_value2]
    username1 = "autotest_1"
    username2 = "autotest_2"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'sg_xattrs_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    continuous = True
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Create CBL database
    sg_client = MobileRestClient()

    # 1. Have a sync function to assign channel1 and verify doc can be accesssed user1 who has access to only channel1
    # Replace with sync function on sgw config to use user xattrs for channels
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username1, password, channels=sg_channels_1, auth=auth)
    auto_user1 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username1, auth=auth)
    sg_client.create_user(sg_admin_url, sg_db, username2, password, channels=sg_channels_2, auth=auth)
    sg_client.create_session(url=sg_admin_url, db=sg_db, name=username2, auth=auth)
    sg_docs = document.create_docs('sg_xattrs', number=1)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=auto_user1)

    # 2.Add  user xattrs via sdk with channel1 with value "xattrs_channel_one"
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value1, xattr=True, create_parents=True)])

    # 3. Verify doc can be accessed by user1, who has  access to only "xattrs_channel_one", but not by user2
    # Configure replication with push_pull
    replicator = Replication(base_url)
    _, _, repl1 = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username1, password, sg_channels_1, sg_client, cbl_db1, sg_blip_url, continuous=continuous, replication_type="push_pull", auth=auth)
    replicator.wait_until_replicator_idle(repl1)
    cbl_doc_count1 = db.getCount(cbl_db1)
    assert cbl_doc_count1 == 1, "doc is not accessible by user1 who has access to 'xattrs_channel_one' "

    _, _, repl2 = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username2, password, sg_channels_2, sg_client, cbl_db2, sg_blip_url, continuous=continuous, replication_type="push_pull", auth=auth)
    replicator.wait_until_replicator_idle(repl2)
    cbl_doc_count2 = db.getCount(cbl_db2)
    assert cbl_doc_count2 == 0, "doc is accessible by user2 who has access to 'xattrs_channel_two'"

    # 4. update the user xattrs via sdk from "xattrs_channel_one" to "xattrs_channel_two"
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value2, xattr=True, create_parents=True)])

    # 5. Verify doc can be accessed by user2 who has  access to only "xattrs_channel_two"
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    time.sleep(5)
    cbl_doc_count1 = db.getCount(cbl_db1)
    cbl_doc_count2 = db.getCount(cbl_db2)
    # 6. change channel to new channel(channel2), verify doc can be accessed only in new channel
    assert cbl_doc_count2 == 1, "doc is not accessible by user2 who has access to 'xattrs_channel_two' "
    # 7. verify user1 cannot access the doc
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user1)["rows"]
    assert len(sg_docs) == 0, "user1 can still access the doc which does not have channel"
    replicator.wait_until_replicator_idle(repl1)
    assert cbl_doc_count1 == 0, "doc is accessible by user1 who has access to only 'xattrs_channel_one'"
    if delta_sync_enabled:
        expvars = sg_client.get_expvars(url=sg_admin_url, auth=auth)
        assert expvars['syncgateway']['per_db'][sg_db]['delta_sync']['deltas_requested'] == 0, "there is a change in delta with expvars change"
        assert expvars['syncgateway']['per_db'][sg_db]['delta_sync']['deltas_sent'] == 0, "there is a change in delta with expvars change"
    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("tombstone_type", [
    pytest.param("delete"),
    pytest.param("expire")
])
def test_tombstone_docs_via_sdk(params_from_base_test_setup, tombstone_type):
    """
    @summary:
        1. Have sync function to update the channels
        2. Enable xattrs and start SGW
        3. Create docs and add user xattrs to the doc and have all docs sync to cbl
        4. have it expired/ delete via SDK in few mins
        5. Verify docs are not accessed via CBL
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sg_channel1_value1 = "xattrs_channel_one"
    sg_channels_1 = [sg_channel1_value1]
    username = "autotest_1"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'sg_xattrs_6'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    continuous = True
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Create CBL database
    sg_client = MobileRestClient()

    # 1. Have sync function to update the channels
    # Replace with sync function on sgw config to use user xattrs for channels
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)

    # 2. Enable xattrs and start SGW
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels_1, auth=auth)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username, auth=auth)

    # 3. Create docs and add user xattrs to the doc and have all docs sync to cbl
    sg_docs = document.create_docs('sg_xattrs', number=10)
    sg_doc_ids = [doc['sgw_uni_id'] for doc in sg_docs]
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=auto_user)
    for id in sg_doc_ids:
        sdk_bucket.mutate_in(id, [SD.upsert(user_custom_channel, sg_channel1_value1, xattr=True, create_parents=True)])

    replicator = Replication(base_url)
    _, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, sg_channels_1, sg_client, cbl_db, sg_blip_url, continuous=continuous, replication_type="push_pull", auth=auth)
    replicator.wait_until_replicator_idle(repl)

    # 4. have obly one doc expired/ delete via SDK in few mins
    if tombstone_type == "delete":
        sdk_bucket.remove(sg_doc_xattrs_id)
    else:
        sdk_bucket.upsert(sg_doc_xattrs_id, {'a_key': 'a_value'})
        sdk_bucket.touch(sg_doc_xattrs_id, ttl=60)

    time.sleep(60)
    retries = 5
    count = 0
    while count < retries:
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
        if len(sg_docs) == 9:
            break
        count += 1
        time.sleep(2)
    sg_doc_ids = [doc['id'] for doc in sg_docs]
    assert sg_doc_xattrs_id not in sg_doc_ids, "user1 can still access the tombstone doc"
    replicator.wait_until_replicator_idle(repl)
    doc_ids = db.getDocIds(cbl_db)
    assert sg_doc_xattrs_id not in doc_ids, "deleted doc vis SDK is still accessible by user"
    replicator.stop(repl)
