import pytest
import time
import random
import requests

from keywords.MobileRestClient import MobileRestClient
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from keywords.SyncGateway import sync_gateway_config_path_for_mode, replace_xattrs_sync_func_in_config
from keywords import document
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.couchbaseserver import get_sdk_client_with_bucket
import couchbase.subdocument as SD
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from libraries.testkit.admin import Admin
from keywords.utils import log_info


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("x509_cert_auth, imports_type", [
    pytest.param(False, "automatic", marks=pytest.mark.ce_sanity),
    pytest.param(False, "ondemand", marks=pytest.mark.sanity)
])
def test_automatic_and_ondemand_imports(params_from_base_test_setup, x509_cert_auth, imports_type):
    """
    @summary:
        https://docs.google.com/spreadsheets/d/15zvscRgX2U2Q1xDpUwYU54G6tVmTv_lMDOSK8G-uzeo/edit#gid=793208277
        "1. Set xattr key in config
        2. Set shared bucket access and import in config for automatic imports and imports off for on demand imports
        3. PUT 2 docs  via SGW
        4. Update 1 doc with SDK to add user xattr
        5. Verify  Import Count stats is 1 for automatic imports and 0 for on demand imports
        6. Perform raw GET only on one doc to ensure added xattr is imported
        7. Import Count stats is  1
        8. Verify raw end point to verify user xattrs with channel added - Covered #33 row
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with sg version below 3.0.0 and xattrs off')
    sg_channel1_value = "abc"
    sg_channels1 = [sg_channel1_value]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'sg_xattrs_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_config = temp_cluster_config

    # 1. Set xattr key in config
    # 2. Set shared bucket access and import in config for automatic imports and imports off for on demand imports
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    if imports_type == "ondemand":
        property = """ "import_docs": false, """
        flag = "{{ autoimport }}"
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, flag, property)

    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    # 3. PUT 2 docs  via SGW
    sg_docs = document.create_docs('sg_xattrs', number=2)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=auto_user)

    # 4. Update doc with SDK to add user xattr
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value, xattr=True, create_parents=True)])

    # 5. Verify  Import Count stats is 1 for automatic imports and 0 for on demand imports
    sg_expvars = sg_client.get_expvars(sg_admin_url)
    sg_import_count = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    if imports_type == "automatic":
        sg_import_count == 1, "doc should get imported automatically when user xattrs added to the doc"
    else:
        sg_import_count == 0, "doc got imported automatically when import_docs is false with user xattrs"
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)

    # 6. Perform raw GET only on one doc to ensure added xattr is imported
    assert raw_doc["_meta"]["xattrs"][user_custom_channel] == sg_channel1_value, "raw doc did not get user xattrs value"

    # 7. Import Count stats is  1
    sg_expvars = sg_client.get_expvars(sg_admin_url)
    sg_import_count = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    sg_import_count == 1, "import_count is not equal to 1 with raw get of the doc"


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("resync", [
    pytest.param(True),
    pytest.param(False)
])
def test_using_resync_and_swapping(params_from_base_test_setup, resync):
    """
    @summary:
    Verify doc won't get updated unless there is on demand import or resync
    Verify doc updated with right channels after swapping the channels through sync functions
    1.Enable xattrs
    2. Have couple of docs with user xattrs("abc") update via sdk
      Have sync function with "abc"
    3. Add user xattrs key on server
      sync_xattrs: {
        channel1 : "abc",
        channel2 : "def"
    }
    4.  update sync function by swapping to new channel  with "def"
    5. Run resync, verify docs are updated and assigned to updated channel
        Verify import_counts stats
    6. Verify syncfn_count is number of docs updated at step4
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('XATTR tests require --xattrs flag')

    sg_channel1_value = "abc"
    sg_channel2_value = "xyz"
    sg_channels1 = [sg_channel1_value]
    sg_channels2 = [sg_channel2_value]
    username = "autotest"
    password = "password"
    xyz_username = "xyzuser"
    user_custom_channel1 = "channel1"
    user_custom_channel2 = "channel2"
    sg_doc_xattrs_id = 'sg_xattrs_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # Set xattr key in config
    # 1. Enable xattrs
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel1)

    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    sg1 = c_cluster.sync_gateways[0]
    admin = Admin(sg1)
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sg_client.create_user(sg_admin_url, sg_db, xyz_username, password, channels=sg_channels2)
    auto_user2 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=xyz_username)
    # 2. Have couple of docs with user xattrs("abc") update via sdk and get syncfn_count
    sg_docs = document.create_docs('sg_xattrs', number=2)
    sg_client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # 3. Add user xattrs key on server
    #   sync_xattrs: {
    #     channel1 : "abc",
    #     channel2 : "def"
    # }
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel1, sg_channel1_value, xattr=True, create_parents=True)])
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel2, sg_channel2_value, xattr=True, create_parents=True)])

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    sg_doc_ids = [doc['id'] for doc in sg_docs]
    assert len(sg_doc_ids) == 1, "channel did not get added to the doc"
    assert sg_doc_xattrs_id in sg_doc_ids, "sg docs is not updated with new channel after resync"

    # 4. update sync function with "def"
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel2)
    sg1.restart(config=temp_sg_config, cluster_config=cluster_config)

    # 5. Run resync, verify docs are updated and assigned to updated channel
    #     Verify import_counts stats
    if resync:
        sg_client.take_db_offline(cluster_conf=cluster_config, db=sg_db)
        status = sg_client.db_resync(url=sg_admin_url, db=sg_db)
        assert status == 200, "re-sync failed"
        sg_client.bring_db_online(cluster_conf=cluster_config, db=sg_db)
        count = 0
        retries = 5
        while True and count < retries:
            db_info = admin.get_db_info("db")
            if db_info["state"] == "Online":
                break
            time.sleep(1)
            count += 1
        sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)
        sg_expvars = sg_client.get_expvars(sg_admin_url)
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=auto_user2)

    else:
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=auto_user)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user2)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    assert len(sg_doc_ids) == 1, "doc is not resynced to new channel"
    assert sg_doc_xattrs_id in sg_doc_ids, "sg docs which has user xattrs did not resynced to new channel"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    assert len(sg_doc_ids) == 0, "doc is not resynced and still accessible to old channel"
    assert sg_doc_xattrs_id not in sg_doc_ids, "sg docs is not updated with new channel after resync"

    # 6. Verify syncfn_count is number of docs updated at step4
    sg_expvars = sg_client.get_expvars(sg_admin_url)
    sg_import_count3 = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    sg_fn_count3 = sg_expvars["syncgateway"]["per_db"][sg_db]["cbl_replication_push"]["sync_function_count"]
    assert sg_import_count3 == 0, "sg import count incremented after the restart though docs are already imported"
    assert sg_fn_count3 == 1, "sync function did not get increamented after the restart though it went through resync process"


@pytest.mark.channels
@pytest.mark.syncgateway
def test_remove_xattrs(params_from_base_test_setup):
    """
    @summary: Covering row #14, #24
    1. Set xattr key in config
    2. Set shared bucket access and import in config
    3. Set channels based on xattr property
        function (doc, oldDoc, meta){
            if (meta.xattrs.myXattr !== undefined){
                channel(meta.xattrs.myXattr);
            }
        }
    4. Add 10 docs on SDK
    5. update user xattrs to only 6 docs via SDk
    6. Verify 6 docs are assigned to the channel which has access to user1
    7. Stop SGW
    8. Remove user_xattr_key in config
    9. Start SGW
    10. Perform a GET of doc as user,  Ensure doc is in same channel as step 5
    11. mutate the doc through via SGW  as user
    12. Ensure channel is updated to reflect no longer having user xattr
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')
    sg_channel1_value = "abc"
    sg_channels1 = [sg_channel1_value]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_conf_name2 = "sync_gateway_default_functional_tests"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_config2 = sync_gateway_config_path_for_mode(sg_conf_name2, mode)

    sg_client = MobileRestClient()

    # 1. Set xattr key in config
    # 2. Set shared bucket access and import in config
    # 3. Set channels based on xattr property
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    sg = c_cluster.sync_gateways[0]
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)

    # 4. Add doc with user xattr on SDK
    sdk_doc_bodies = document.create_docs('sdk', number=10)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_client.upsert_multi(sdk_docs)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]

    filtered_doc_ids = random.sample(sdk_doc_ids, 6)
    non_filtered_ids = set(sdk_doc_ids) - set(filtered_doc_ids)
    for doc_id in filtered_doc_ids:
        sdk_client.mutate_in(doc_id, [SD.upsert(user_custom_channel, sg_channel1_value, xattr=True, create_parents=True)])

    # 5. Ensure doc is in with chosen channel
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 6, "sg docs are not added to the channel which auto user belongs to"
    sg_doc_ids = [row["id"] for row in sg_docs]
    for doc_id in filtered_doc_ids:
        assert doc_id in sg_doc_ids

    for doc_id in non_filtered_ids:
        assert doc_id not in sg_doc_ids

    # 6. Stop SGW
    sg.stop()

    # 7. Remove user_xattr_key in config
    # 8. Start SGW
    sg.start(config=sg_config2)

    # 9. Perform a GET of doc as user,  Ensure doc is in same channel as step 5
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 6, "sg docs got removed before update of docs"

    # 10. mutate the doc via SGW  as user
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=auto_user)

    # 11. Ensure channel is updated to reflect no longer having user xattr
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 0, "user xattrs removal is not reflected and did not update the channels"


@pytest.mark.channels
@pytest.mark.syncgateway
def test_sync_xattrs_update_concurrently(params_from_base_test_setup):
    """
    @summary:
    1. Set xattr key in config
    2. Set shared bucket access and import in config
    3. Set channels based on xattr property
        function (doc, oldDoc, meta){
            if (meta.xattrs.myXattr !== undefined){
                channel(meta.xattrs.myXattr);
            }
        }
    4. Add doc with user xattr on SDK
    5. Ensure doc is in with chosen channel
    6. Multiprocess to update user xattrs to replace to new value to old channel and process sync function with new channel by getting all docs
    7. Ensure old user1 cannot access the docs anymore
    8. Ensure new user can access the docs anymore
       Below above steps verifies that docs land on right channel without any issues
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    num_docs = 20
    sg_channel1_value = "abc"
    sg_channel2_value = "xyz"
    sg_channels1 = [sg_channel1_value]
    sg_channels2 = [sg_channel2_value]
    username = "autotest"
    username2 = "xyzuser"
    password = "password"
    user_custom_channel = "channel1"
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Set xattr key in config
    # 2. Set shared bucket access and import in config
    # 3. Set channels based on xattr property
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sg_client.create_user(sg_admin_url, sg_db, username2, password, channels=sg_channels2)
    auto_user2 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username2)

    # 4. Add doc with user xattr on SDK
    sdk_doc_bodies = document.create_docs('sdk', number=num_docs)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)
    count = 0
    retries = 10
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]
    while count < retries and len(sg_docs) < num_docs:
        time.sleep(1)
        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]
        count += 1
    sg_doc_ids = [row["id"] for row in sg_docs]

    sg_docs_via_sdk_get = sdk_client.get_multi(sg_doc_ids)
    for doc_id, _ in list(sg_docs_via_sdk_get.items()):
        sdk_client.mutate_in(doc_id, [SD.upsert(user_custom_channel, sg_channel1_value, xattr=True, create_parents=True)])

    # 5. Ensure doc is in with chosen channel
    count = 0
    retries = 10
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    while count < retries and len(sg_docs) < num_docs:
        time.sleep(1)
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
        count += 1
    assert len(sg_docs) == num_docs, "sg docs did not assigned to the user xattrs channels"

    # 6. Multiprocess to update user xattrs and process sync function with new channel by getting all docs
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_user_xattrs_task = tpe.submit(update_user_xattrs, sdk_client, user_custom_channel, sg_channel2_value, sg_doc_ids)
        for i in range(20):
            sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user2)["rows"]
        update_user_xattrs_task.result()

    # 7. Ensure old user1 cannot access the docs anymore
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 0, "docs still exist in old channel even after replacing the user xattrs"

    # 8. Ensure new user can access the docs anymore
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user2)["rows"]
    assert len(sg_docs) == 20, "docs did not get updated to new channel even after replacing the user xattrs"


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("channel_type", [
    pytest.param("list"),
    pytest.param("string"),
    pytest.param("special_characters"),
])
def test_syncfunction_user_xattrs_format(params_from_base_test_setup, channel_type):
    """
    @summary:
        "1. Set xattr key in config
        2. Set shared bucket access and import in config for automatic imports and imports off for on demand imports
        3. PUT 1 docs  via SGW
        4. Update 1 doc with SDK to add user xattr and have user xattrs with map
        5. Verify the doc in SGW
        covered # 18, 19, 20 rows
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    if channel_type == "string":
        sg_channel1_value1 = "abc"
    elif channel_type == "list":
        sg_channel1_value1 = ["abc", "xyz"]
    else:
        sg_channel1_value1 = "*(-_%"
    sg_channels1 = [sg_channel1_value1]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'user_xattrs_format_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Set xattr key in config
    # 2. Set shared bucket access and import in config for automatic imports and imports off for on demand imports
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    if channel_type == "string" or channel_type == "special_characters":
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    else:
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channel1_value1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    # 3. PUT 2 docs  via SGW
    sg_docs = document.create_docs('user_xattrs_format', number=2)
    sg_client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # 4. Update doc with SDK to add user xattr
    sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value1, xattr=True, create_parents=True)])
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 1, "docs still exist in old channel even after replacing the user xattrs"


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("data_type", [
    pytest.param("boolean"),
    pytest.param("dictionary"),
    pytest.param("integer")
])
def test_syncfunction_user_xattrs_dictionary_boolean_integer(params_from_base_test_setup, data_type):
    """
    @summary:
        1. Set xattr key in config
        2. Enable xattrs
        3. Have a sync funtion for boolean/dictionary/integer
        4. Also enable user_xattrs_key on channel1, channel2 on sync config
        5. create 2 docs  via SGW
        6. Update 1 doc (doc1) with SDK to add user xattr and have user xattrs with boolean
        7. verify doc1 is assign to channel 'abc' when channel1 is true otherwise 'xyz'
        covered # 17, 21, 22 rows
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sgw_channel_value1 = "ch_abc"
    sgw_channel_value2 = "ch_xyz"
    if data_type == "boolean":
        channel_value1 = True
        channel_value2 = False
    elif data_type == "integer":
        channel_value1 = 5
        channel_value2 = 5
    else:
        channel_value1 = {"value1": True, "value2": "ch_abc", "value3": "ch_xyz"}
        channel_value2 = {"value1": False, "value2": "ch_abc", "value3": "ch_xyz"}
    sg_channels1 = [sgw_channel_value1]
    sg_channels2 = [sgw_channel_value2]
    username1 = "abc_autotest"
    username2 = "xyz_autotest"
    password = "password"
    user_custom_channel1 = "channel1"
    sg_doc_xattrs_id0 = 'user_xattrs_format_0'
    sg_doc_xattrs_id1 = 'user_xattrs_format_1'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Set xattr key in config
    # 2. Enable xattrs
    # 3. Have a sync funtion to verify if channel1 value1 is True then assign the doc to the channel 'abc' , otherwise 'xyz'
    # 4. Also enable user_xattrs_key on channel1 on sync config
    temp_sg_config = update_doctype_by_syncfn(sg_config, user_custom_channel1, data_type)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username1, password, channels=sg_channels1)
    sg_client.create_user(sg_admin_url, sg_db, username2, password, channels=sg_channels2)
    auto_user1 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username1)
    auto_user2 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username2)
    # 5. create 2 docs  via SGW
    sg_docs = document.create_docs('user_xattrs_format', content="doc-content", number=2)
    sg_client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # 6. Update 1 doc (doc1) with SDK to add user xattr and have user xattrs with boolean
    sdk_bucket.mutate_in(sg_doc_xattrs_id0, [SD.upsert(user_custom_channel1, channel_value1, xattr=True, create_parents=True)])
    sdk_bucket.mutate_in(sg_doc_xattrs_id1, [SD.upsert(user_custom_channel1, channel_value2, xattr=True, create_parents=True)])
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]

    # 7. verify doc1 is assign to channel 'abc' when channel1 is true otherwise 'xyz'
    if data_type == "integer":
        time.sleep(channel_value1)  # for integer sync function written to expiry with the given integer value, so wait until it is expired
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user1)["rows"]
    if data_type == "integer":
        assert len(sg_docs) == 0, "docs still exist in old channel even after replacing the user xattrs"
    else:
        assert len(sg_docs) == 1, "docs still exist in old channel even after replacing the user xattrs"
        sg_doc_ids = [row["id"] for row in sg_docs]
        assert sg_doc_xattrs_id0 in sg_doc_ids, "user_xattrs_0 is not assigned based on sync function and user xattrs"

    if data_type != "integer":
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user2)["rows"]
        assert len(sg_docs) == 1, "docs are not assigned to right channel according to sync function"
        sg_doc_ids = [row["id"] for row in sg_docs]
        assert sg_doc_xattrs_id1 in sg_doc_ids, "user_xattrs_1 is not assigned based on sync function and user xattrs"


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("missing_type", [
    pytest.param("user_xattrs_key"),
    pytest.param("server_user_xattrs"),
])
def test_missing_xattrs_key(params_from_base_test_setup, missing_type):
    """
    @summary:
    https://docs.google.com/spreadsheets/d/15zvscRgX2U2Q1xDpUwYU54G6tVmTv_lMDOSK8G-uzeo/edit#gid=793208277
    covers #28, 29, 30
    1. Set shared bucket access and import in config
    2. Write a sync function to assign new channel using xattr value without adding xattrs key enabled
    3. Verify SGW starts successfully
    4. create doc via SGW rest api
    5. Update doc with SDK to add user xattr
    6. Verify docs are not assigned to the channel which defined in user xattrs
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if sync_gateway_version < "3.0.0":
        pytest.skip('SGW version is not 3.0 and above')

    if missing_type != "xattrs_disabled" and not xattrs_enabled:
        pytest.skip('Test did not enable xattrs')
    if missing_type == "xattrs_disabled" and xattrs_enabled:
        pytest.skip('Param with xattrs disabled expected to disable xattrs')
    sg_channel1_value = "abc"
    sg_channels1 = [sg_channel1_value]
    username = "autotest"
    password = "password"
    user_custom_channel1 = "channel1"
    doc_xattrs_id = 'user_xattrs_format_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Set shared bucket access and import in config
    # 2. Write a sync function to assign new channel using xattr value without adding xattrs key enabled
    # 3. Verify SGW starts successfully
    if missing_type == "user_xattrs_key":
        temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel1, enable_xattrs_key=False)
    else:
        temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel1)

    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)

    # 4. create doc via SGW rest api
    sg_docs = document.create_docs('user_xattrs_format', number=2)
    sg_client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # 5. Update doc with SDK to add user xattr
    if missing_type != "server_user_xattrs":
        sdk_bucket.mutate_in(doc_xattrs_id, [SD.upsert(user_custom_channel1, sg_channel1_value, xattr=True, create_parents=True)])

    # 6. Verify docs are not assigned to the channel which defined in user xattrs
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=auto_user)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 0, "docs assigned to the channel without user xattrs key"

    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, doc_xattrs_id)

    if missing_type == "user_xattrs_key":
        try:
            raw_doc["_meta"]["xattrs"][user_custom_channel1]
            assert False, "did not catch the KeyError exception"
        except KeyError as ke:
            assert '_meta' in str(ke), "did not get the _meta key error"
    else:
        assert raw_doc["_meta"]["xattrs"][user_custom_channel1] is None, "raw doc has _meta xattrs with user xattrs key missing on sgw config "


@pytest.mark.channels
@pytest.mark.syncgateway
def test_xattrs_key_with_disabled_xattrs(params_from_base_test_setup):
    """
    @summary:
    https://docs.google.com/spreadsheets/d/15zvscRgX2U2Q1xDpUwYU54G6tVmTv_lMDOSK8G-uzeo/edit#gid=793208277
    covers #26
    1. Disable xattrs and enable user xattrs key in sgw config
    2. Verify SGW throws an error when starting the sgw
    """

    sg_url = params_from_base_test_setup["sg_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if sync_gateway_version < "3.0.0" or xattrs_enabled:
        pytest.skip('SGW version is not 3.0 and above or xattrs has to be disabled')

    user_custom_channel1 = "channel1"
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ user_xattrs_key }}", "")
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ sync_func }}", """ "" """)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)
    sg = c_cluster.sync_gateways[0]

    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel1)

    with ProcessPoolExecutor(max_workers=2) as mp:
        sgrestart = mp.submit(sg.restart, temp_sg_config, cluster_config)
        time.sleep(60)
    sgrestart.result(timeout=80)

    try:
        requests.get(sg_url, timeout=30)
        assert False, "Sync gateway started successfully with xattrs disabled and xattrs key enabled "
    except Exception as he:
        log_info(str(he))
        log_info("Expected to have sync gateway fail to start")


@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("update_source", [
    pytest.param("sdk"),
    pytest.param("sgw")
])
def test_rev_with_docupdates_docxattrsupdate(params_from_base_test_setup, update_source):
    """
    @summary:
        1. have sync function :
        function (doc, oldDoc, meta){
        if (meta.xattrs.myXattr !== undefined){
            channel(meta.xattrs.myXattr);
        }
        }
        Start SGW
        2. Create doc in SGW
        3. Get revision of the doc
        4. Update user xattrs on docs via sdk :
        sync_xattrs: {
            channel1 : ""abc1"",
            channel2 : ""abc2""
        }
        5. Also  update doc via sdk and then via SGW
        6. Wait until docs imported and docs processed via sync function and verify the revision generated and incremented by 1
    """
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sg_channel1_value1 = "abc"

    sg_channels1 = [sg_channel1_value1]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'user_xattrs_format_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_client = MobileRestClient()

    # 1. have sync function with xattrs key and channel assignment of user xattrs
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)

    # 2. Create doc in SGW
    sg_docs = document.create_docs('user_xattrs_format', content="sgw-content", number=2)
    sg_client.add_bulk_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # 3. Get revision of the doc
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)
    rev_gen1 = int(raw_doc["_sync"]["rev"].split("-")[0])

    # 4. Update user xattrs on docs via sdk
    # 5. Also  update doc via sdk/SGW in parallel
    if update_source == "sdk":
        sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value1, xattr=True, create_parents=True)])
        sdk_doc = sdk_bucket.get(sg_doc_xattrs_id)
        doc_body = sdk_doc.value
        doc_body['content'] = "updated_doc_content"
        sdk_bucket.upsert(sg_doc_xattrs_id, doc_body)
    else:
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
        sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, sg_channel1_value1, xattr=True, create_parents=True)])
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=sg_doc_xattrs_id, number_updates=1, auth=auto_user)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auto_user)["rows"]
    assert len(sg_docs) == 1, "docs still exist in old channel even after replacing the user xattrs"

    # 6. Wait until docs imported and docs processed via sync function and verify the revision generated and incremented by 1
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)
    rev_gen2 = int(raw_doc["_sync"]["rev"].split("-")[0])
    assert rev_gen2 == rev_gen1 + 1, "revision did not get incremented though there is a update on doc via SDK"


@pytest.mark.channels
@pytest.mark.syncgateway
def test_rev_generation_with_largexattrs(params_from_base_test_setup):
    """
    @summary:
        1. Have sync function with xattrs key and channel assignment of user xattrs
            function (doc, oldDoc, meta){
            if (meta.xattrs.myXattr !== undefined){
                channel(meta.xattrs.myXattr);
            }
            }
        2. Create doc in SDK
        3. Wait until docs imported to SGW
        4. Update user xattrs with 25 channels on docs via sdk :
        sync_xattrs: {
            channel1 : ""abc1"",
            channel2 : ""abc2"",
                |
                |
                |
                |
                |
                |
            may be to 25 channels
            channel25 : ""abc25""
        }
        5. Verfy no rev changes. verify delta _sync stats
    """
    sg_db = "db"
    # sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if not xattrs_enabled or sync_gateway_version < "3.0.0":
        pytest.skip('Test did not enable xattrs or sgw version is not 3.0 and above')

    sg_channel1_value1 = "abc"

    sg_channels1 = [sg_channel1_value1]
    username = "autotest"
    password = "password"
    user_custom_channel = "channel1"
    sg_doc_xattrs_id = 'sdk_0'
    sg_conf_name = "custom_sync/sync_gateway_custom_sync"
    number_of_sdk_docs = 1
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    sg_client = MobileRestClient()

    # 1. Have sync function with xattrs key and channel assignment of user xattrs
    temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, user_custom_channel)
    c_cluster = cluster.Cluster(config=cluster_config)
    c_cluster.reset(sg_config_path=temp_sg_config)

    cbs_ip = c_cluster.servers[0].host
    sg1 = c_cluster.sync_gateways[0]
    cbs_bucket = c_cluster.servers[0].get_bucket_names()[0]
    sdk_bucket = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=sg_channels1)
    # auto_user = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    # 2. Create doc in SDK
    sdk_doc_bodies = document.create_docs('sdk', number=number_of_sdk_docs)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    # sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_bucket.upsert_multi(sdk_docs)

    # 3. Wait until docs imported to SGW
    retries = 3
    count = 0
    while count < retries:
        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)["rows"]
        if len(sg_docs) >= number_of_sdk_docs:
            break
        else:
            count += 1
            time.sleep(1)

    # Get revision before the update
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)
    rev_gen1 = int(raw_doc["_sync"]["rev"].split("-")[0])

    # 4. Update user xattrs with 25 channels on docs via sdk
    channel_list = []
    for i in range(25):
        channel_value = "channel" + str(i)
        channel_list.append(channel_value)
        sdk_bucket.mutate_in(sg_doc_xattrs_id, [SD.upsert(user_custom_channel, channel_value, xattr=True, create_parents=True)])

    for i in range(10):
        channel_item = random.choice(channel_list)
        temp_sg_config = replace_xattrs_sync_func_in_config(sg_config, channel_item)
        sg1.restart(config=temp_sg_config, cluster_config=cluster_config)

    # 5. Verfy no rev changes. verify delta _sync stats
    raw_doc = sg_client.get_raw_doc(sg_admin_url, sg_db, sg_doc_xattrs_id)
    rev_gen2 = int(raw_doc["_sync"]["rev"].split("-")[0])
    assert rev_gen2 == rev_gen1, "revision did not get incremented though there is a update on doc via SDK"


def update_user_xattrs(sdk_client, channel, channel_value, doc_ids):
    sg_docs_via_sdk_get = sdk_client.get_multi(doc_ids)
    for doc_id, _ in list(sg_docs_via_sdk_get.items()):
        sdk_client.mutate_in(doc_id, [SD.replace(channel, channel_value, xattr=True)])


def update_doctype_by_syncfn(sg_config, channel1, data_type):
    # Sample config how it looks after it constructs the config here
    """function (doc, oldDoc, meta){
    if(meta.xattrs.channel1 != undefined){
        channel(meta.xattrs.channel1);
    }
    }"""
    if data_type == "boolean":
        sync_func_string = """ `function (doc, oldDoc, meta){
        if(meta.xattrs.""" + channel1 + """ != undefined){
            if(meta.xattrs.""" + channel1 + """){
                channel("ch_abc");
            } else {
                channel("ch_xyz");
            }
        }
        }` """
    elif data_type == "integer":
        sync_func_string = """ `function (doc, oldDoc, meta){
        if(meta.xattrs.""" + channel1 + """ != undefined){
            console.log("have channel1")
            expiry(meta.xattrs.""" + channel1 + """);
        }
        }` """
    else:
        sync_func_string = """ `function (doc, oldDoc, meta){
        if(meta.xattrs.""" + channel1 + """ != undefined){
            if(meta.xattrs.""" + channel1 + """.value1){
                channel(meta.xattrs.""" + channel1 + """.value2);
            } else {
                channel(meta.xattrs.""" + channel1 + """.value3);
            }
        }
        }` """
    mode = "cc"

    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, mode)
    user_xattrs_string = """ "user_xattr_key": "{}", """.format(channel1)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ user_xattrs_key }}", user_xattrs_string)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ sync_func }}", sync_func_string)
    return temp_sg_config
