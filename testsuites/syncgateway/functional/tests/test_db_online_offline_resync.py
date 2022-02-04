from libraries.testkit.verify import verify_changes
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient

import time
import pytest

from libraries.testkit.admin import Admin
from multiprocessing.pool import ThreadPool
from requests.exceptions import HTTPError
from libraries.testkit.parallelize import in_parallel
from requests.auth import HTTPBasicAuth
from keywords.constants import RBAC_FULL_ADMIN

from keywords.utils import log_info
from keywords.utils import log_error
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf


@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.basicauth
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions, x509_cert_auth", [
    pytest.param("bucket_online_offline/db_online_offline_access_all", 5, 100, 10, True, marks=pytest.mark.sanity),
    pytest.param("bucket_online_offline/db_online_offline_access_all", 5, 100, 10, False, marks=pytest.mark.oscertify)
])
def test_bucket_online_offline_resync_sanity(params_from_base_test_setup, sg_conf_name, num_users, num_docs,
                                             num_revisions, x509_cert_auth):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    start = time.time()

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, test_mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_conf = temp_cluster_config

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    if auth:
        admin.auth = HTTPBasicAuth(auth[0], auth[1])
    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    bulk = True
    in_parallel(user_objects, 'add_docs', num_docs, bulk)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in list(recieved_docs.items()):
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in list(docs_rev_dict.items()):
        for doc_id in list(docs_revision_dict.keys()):
            rev = docs_revision_dict[doc_id]
            log_info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log_error('User {} doc_id {} got revision {}, expected revision {}'.format(
                    user_obj.name,
                    doc_id,
                    rev,
                    expected_revision)
                )

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in list(output.values())

    # Take "db" offline
    sg_client = MobileRestClient()
    status = sg_client.take_db_offline(cluster_conf=cluster_conf, db="db")
    assert status == 0

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config,
                                                      cluster_config=cluster_conf)
    assert restart_status == 0
    retries = 0
    if sync_gateway_version < "3.0.0":
        while retries < 5:
            try:
                num_changes = admin.db_resync(db="db")
                log_info("expecting num_changes {} == num_docs {} * num_users {}".format(num_changes, num_docs, num_users))
                assert num_changes['payload']['changes'] == num_docs * num_users
                break
            except AssertionError as error:
                retries = retries + 1
                time.sleep(3)
                if retries == 5:
                    raise error
    else:
        resync_status = admin.db_resync(db="db")
        while resync_status != "stopped" and retries < 50:
            resync_status = admin.db_get_resync_status(db="db")
            retries = retries + 1
            time.sleep(2)
        log_info("expecting num_changes {} == num_docs {} * num_users {}".format(resync_status, num_docs, num_users))
        assert resync_status['payload']['docs_changed'] == num_docs * num_users, "docs_changed did not match with total docs of all users"
    # Take "db" online
    retries = 0
    while retries < 5:
        try:
            status = sg_client.bring_db_online(cluster_conf=cluster_conf, db="db")
            assert status == 0
            break
        except AssertionError as error:
            retries = retries + 1
            time.sleep(2)
            if retries == 5:
                raise error

    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in list(user_cache.items())}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    end = time.time()
    log_info("Test ended.")
    log_info("Main test duration: {}".format(end - init_completed))
    log_info("Test setup time: {}".format(init_completed - start))
    log_info("Total Time taken: {}s".format(end - start))


# implements scenario: 11
# With DB in online state, put a large number of docs (enough to cause _resync to run for 10-15 seconds),
# put DB offline, run _resync, attempt to bring DB online while _resync is running,
# expected result _online will fail with status 503, when _resync is complete,
# attempt to bring DB _online, expected result _online will succeed, return status 200.
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("bucket_online_offline/db_online_offline_access_all", 5, 100, 10),
])
def test_bucket_online_offline_resync_with_online(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):
    log_info("Starting test...")
    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_with_online'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    if auth:
        admin.auth = HTTPBasicAuth(auth[0], auth[1])
    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    bulk = True
    in_parallel(user_objects, 'add_docs', num_docs, bulk)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    # 100 docs are updating is faster now and removing the time.sleep(10) here.
    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in list(recieved_docs.items()):
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in list(docs_rev_dict.items()):
        for doc_id in list(docs_revision_dict.keys()):
            rev = docs_revision_dict[doc_id]
            log_info('User {} doc_id {} has {} revisions, expected revision: {}'.format(
                user_obj.name,
                doc_id,
                rev,
                expected_revision)
            )
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log_error('User {} doc_id {} got revision {}, expected revision {}'.format(
                    user_obj.name,
                    doc_id,
                    rev,
                    expected_revision)
                )

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in list(output.values())

    # Take "db" offline
    sg_client = MobileRestClient()
    status = sg_client.take_db_offline(cluster_conf=cluster_conf, db="db")
    assert status == 0

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config,
                                                      cluster_config=cluster_conf)
    assert restart_status == 0

    pool = ThreadPool(processes=1)

    log_info("Restarted SG....")

    retries = 0
    while retries < 5:
        try:
            db_info = admin.get_db_info("db")
            log_info("Status of db = {}".format(db_info["state"]))
            assert db_info["state"] == "Offline"
            break
        except AssertionError as error:
            time.sleep(2)
            log_info("Sleeping....")
            retries = retries + 1
            if retries == 5:
                raise error

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log_info("resync issued !!!!!!")
    except Exception as e:
        log_info("Catch resync exception: {}".format(e))

    verify_resync_changes(sync_gateway_version, async_resync_result, num_docs, num_users, admin)
    resync_occured = False
    for i in range(20):
        db_info = admin.get_db_info("db")
        log_info("Status of db = {}".format(db_info["state"]))
        if db_info["state"] == "Resyncing":
            resync_occured = True
            log_info("Resync occured")
            try:
                status = sg_client.bring_db_online(cluster_conf=cluster_conf, db="db")
                log_info("online issued !!!!!online request status: {}".format(status))
            except HTTPError as e:
                log_info("status = {} exception = {}".format(status, e.response.status_code))
                if e.response.status_code == 503:
                    log_info("Got correct error code")
                else:
                    log_info("Got some other error failing test")
                    assert False
        if resync_occured:
            break

    retries = 0
    while retries < 8:
        try:
            status = sg_client.bring_db_online(cluster_conf=cluster_conf, db="db")
            assert status == 0
            log_info("online request issued !!!!! response status: {}".format(status))
            db_info = admin.get_db_info("db")
            log_info("Status of db = {}".format(db_info["state"]))
            assert db_info["state"] == "Online"
            break
        except AssertionError as error:
            retries = retries + 1
            time.sleep(5)
            if retries == 8:
                raise error

    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in list(user_cache.items())}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    end = time.time()
    log_info("Test ended.")
    log_info("Main test duration: {}".format(end - init_completed))
    log_info("Test setup time: {}".format(init_completed - start))
    log_info("Total Time taken: {}s".format(end - start))


# implements scenario: 12 and 13
# While DB is running _resync make REST API calls against DB for supported offline operations,
# GET db status, PUT DB config, expected result calls should return status 200.
# #13
# With DB running a _resync, make REST API call to get DB runtime details /db/,
# expected result 'state' property with value 'Resyncing' is returned.
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("bucket_online_offline/db_online_offline_access_all", 5, 100, 10),
])
def test_bucket_online_offline_resync_with_offline(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):
    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_with_online'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    if auth:
        admin.auth = HTTPBasicAuth(auth[0], auth[1])
    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    bulk = True
    in_parallel(user_objects, 'add_docs', num_docs, bulk)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in list(recieved_docs.items()):
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in list(docs_rev_dict.items()):
        for doc_id in list(docs_revision_dict.keys()):
            rev = docs_revision_dict[doc_id]
            log_info('User {} doc_id {} has {} revisions, expected revision: {}'.format(
                user_obj.name,
                doc_id,
                rev,
                expected_revision
            ))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log_error('User {} doc_id {} got revision {}, expected revision {}'.format(
                    user_obj.name,
                    doc_id,
                    rev,
                    expected_revision
                ))

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in list(output.values())

    # Take "db" offline
    sg_client = MobileRestClient()
    status = sg_client.take_db_offline(cluster_conf=cluster_conf, db="db")
    assert status == 0

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config,
                                                      cluster_config=cluster_conf)
    assert restart_status == 0

    pool = ThreadPool(processes=1)
    log_info("Restarted SG....")

    retries = 0
    while retries < 7:
        try:
            db_info = admin.get_db_info("db")
            log_info("Status of db = {}".format(db_info["state"]))
            assert db_info["state"] == "Offline"
            break
        except AssertionError as error:
            retries = retries + 1
            time.sleep(2)
            if retries == 7:
                raise error

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log_info("resync issued !!!!!!")
    except Exception as e:
        log_info("Catch resync exception: {}".format(e))

    verify_resync_changes(sync_gateway_version, async_resync_result, num_docs, num_users, admin)
    resync_occured = False
    for i in range(20):
        db_info = admin.get_db_info("db")
        log_info("Status of db = {}".format(db_info["state"]))
        if db_info["state"] == "Resyncing":
            resync_occured = True
            log_info("Resync occured")
            try:
                status = admin.get_db_info(db="db")
                log_info("Got db_info request status: {}".format(status))
            except HTTPError as e:
                log_info("status = {} exception = {}".format(status, e.response.status_code))
                assert False
            else:
                log_info("Got 200 ok for supported operation")

        time.sleep(1)
        if resync_occured:
            break

    retries = 0
    while retries < 10:
        try:
            status = sg_client.bring_db_online(cluster_conf=cluster_conf, db="db")
            log_info("online request issued !!!!! response status: {}".format(status))
            db_info = admin.get_db_info("db")
            log_info("Status of db = {}".format(db_info["state"]))
            assert db_info["state"] == "Online"
            break
        except AssertionError as error:
            log_info("Status of db = {}".format(db_info["state"]))
            retries = retries + 1
            time.sleep(3)
            if retries == 10:
                raise error

    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in list(user_cache.items())}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    end = time.time()
    log_info("Test ended.")
    log_info("Main test duration: {}".format(end - init_completed))
    log_info("Test setup time: {}".format(init_completed - start))
    log_info("Total Time taken: {}s".format(end - start))


def verify_resync_changes(sync_gateway_version, async_resync_result, num_docs, num_users, admin):
    if sync_gateway_version < "3.0.0":
        resync_result = async_resync_result.get()
        log_info("resync_changes {}".format(resync_result))
        log_info("expecting num_changes  == num_docs {} * num_users {}".format(num_docs, num_users))
        assert resync_result['payload']['changes'] == num_docs * num_users
        assert resync_result['status_code'] == 200
    else:
        retries = 0
        resync_result = admin.db_get_resync_status(db="db")
        while resync_result != "stopped" and retries < 50:
            resync_result = admin.db_get_resync_status(db="db")
            retries = retries + 1
            time.sleep(2)
        log_info("expecting num_changes  == num_docs {} * num_users {}".format(num_docs, num_users))
        assert resync_result['payload']['docs_changed'] == num_docs * num_users
        assert resync_result['status_code'] == 200
