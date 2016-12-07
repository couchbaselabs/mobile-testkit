from libraries.testkit.verify import verify_changes
from libraries.testkit.cluster import Cluster

import time
import pytest

from libraries.testkit.admin import Admin
from multiprocessing.pool import ThreadPool
from requests.exceptions import HTTPError
from libraries.testkit.parallelize import in_parallel

from keywords.utils import log_info
from keywords.utils import log_error
from keywords.SyncGateway import sync_gateway_config_path_for_mode


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("bucket_online_offline/db_online_offline_access_all", 5, 100, 10),
])
def test_bucket_online_offline_resync_sanity(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_sanity'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    start = time.time()

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in docs_rev_dict.items():
        for doc_id in docs_revision_dict.keys():
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
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert status == 200

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config)
    assert restart_status == 0

    time.sleep(10)

    num_changes = admin.db_resync(db="db")
    log_info("expecting num_changes {} == num_docs {} * num_users {}".format(num_changes, num_docs, num_users))
    assert num_changes['payload']['changes'] == num_docs * num_users

    status = admin.bring_db_online(db="db")
    assert status == 200

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

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
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("bucket_online_offline/db_online_offline_access_all", 5, 100, 10),
])
def test_bucket_online_offline_resync_with_online(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):
    log_info("Starting test...")
    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_with_online'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in docs_rev_dict.items():
        for doc_id in docs_revision_dict.keys():
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
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert status == 200

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config)
    assert restart_status == 0

    log_info("Sleeping....")
    time.sleep(10)
    pool = ThreadPool(processes=1)

    log_info("Restarted SG....")
    time.sleep(5)

    db_info = admin.get_db_info("db")
    log_info("Status of db = {}".format(db_info["state"]))
    assert db_info["state"] == "Offline"

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log_info("resync issued !!!!!!")
    except Exception as e:
        log_info("Catch resync exception: {}".format(e))

    time.sleep(1)
    resync_occured = False

    for i in range(20):
        db_info = admin.get_db_info("db")
        log_info("Status of db = {}".format(db_info["state"]))
        if db_info["state"] == "Resyncing":
            resync_occured = True
            log_info("Resync occured")
            try:
                status = admin.bring_db_online(db="db")
                log_info("online issued !!!!!online request status: {}".format(status))
            except HTTPError as e:
                log_info("status = {} exception = {}".format(status, e.response.status_code))
                if e.response.status_code == 503:
                    log_info("Got correct error code")
                else:
                    log_info("Got some other error failing test")
                    assert False

        time.sleep(1)
        if resync_occured:
            break

    time.sleep(10)

    status = admin.bring_db_online(db="db")
    log_info("online request issued !!!!! response status: {}".format(status))

    time.sleep(5)
    db_info = admin.get_db_info("db")
    log_info("Status of db = {}".format(db_info["state"]))
    assert db_info["state"] == "Online"

    resync_result = async_resync_result.get()
    log_info("resync_changes {}".format(resync_result))
    log_info("expecting num_changes  == num_docs {} * num_users {}".format(num_docs, num_users))
    assert resync_result['payload']['changes'] == num_docs * num_users
    assert resync_result['status_code'] == 200

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

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
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("bucket_online_offline/db_online_offline_access_all", 5, 100, 10),
])
def test_bucket_online_offline_resync_with_offline(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):
    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    test_mode = params_from_base_test_setup["mode"]

    if test_mode == "di":
        pytest.skip("Unsupported feature in distributed index")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, test_mode)

    log_info("Running 'test_bucket_online_offline_resync_with_online'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in docs_rev_dict.items():
        for doc_id in docs_revision_dict.keys():
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
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert status == 200

    sg_restart_config = sync_gateway_config_path_for_mode("bucket_online_offline/db_online_offline_access_restricted", test_mode)
    restart_status = cluster.sync_gateways[0].restart(sg_restart_config)
    assert restart_status == 0

    log_info("Sleeping....")
    time.sleep(10)
    pool = ThreadPool(processes=1)

    log_info("Restarted SG....")
    time.sleep(5)

    db_info = admin.get_db_info("db")
    log_info("Status of db = {}".format(db_info["state"]))
    assert db_info["state"] == "Offline"

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log_info("resync issued !!!!!!")
    except Exception as e:
        log_info("Catch resync exception: {}".format(e))

    time.sleep(1)
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

    time.sleep(10)

    status = admin.bring_db_online(db="db")
    log_info("online request issued !!!!! response status: {}".format(status))

    time.sleep(5)
    db_info = admin.get_db_info("db")
    log_info("Status of db = {}".format(db_info["state"]))
    assert db_info["state"] == "Online"

    resync_result = async_resync_result.get()
    log_info("resync_changes {}".format(resync_result))
    log_info("expecting num_changes  == num_docs {} * num_users {}".format(num_docs, num_users))
    assert resync_result['payload']['changes'] == num_docs * num_users
    assert resync_result['status_code'] == 200

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    end = time.time()
    log_info("Test ended.")
    log_info("Main test duration: {}".format(end - init_completed))
    log_info("Test setup time: {}".format(init_completed - start))
    log_info("Total Time taken: {}s".format(end - start))
