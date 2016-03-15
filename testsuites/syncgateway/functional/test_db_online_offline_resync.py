from testkit.verify import verify_changes
from testkit.cluster import Cluster

import time
from testkit.admin import Admin
from multiprocessing.pool import ThreadPool
from requests.exceptions import HTTPError
from testkit.parallelize import *
import logging
log = logging.getLogger(settings.LOGGER)


def test_bucket_online_offline_resync_sanity(num_users, num_docs, num_revisions):
    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset("resources/sync_gateway_configs/bucket_online_offline/db_online_offline_access_all_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log.info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
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
            log.info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log.error('User {} doc_id got revision {}, expected revision {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    restart_status = cluster.sync_gateways[0].restart("bucket_online_offline/db_online_offline_access_restricted_cc.json")
    assert restart_status == 0

    time.sleep(10)

    num_changes = admin.db_resync(db="db")
    log.info("expecting num_changes {} == num_docs {} * num_users {}".format(num_changes, num_docs, num_users))
    assert(num_changes['payload']['changes'] == num_docs * num_users)

    status = admin.bring_db_online(db="db")
    assert(status == 200)

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    log.info("Test ended.")
    log.info("Main test duration: {}".format(end - init_completed))
    log.info("Test setup time: {}".format(init_completed - start))
    log.info("Total Time taken: {}s".format(end - start))


# implements scenario: 11
# With DB in online state, put a large number of docs (enough to cause _resync to run for 10-15 seconds),
# put DB offline, run _resync, attempt to bring DB online while _resync is running,
# expected result _online will fail with status 503, when _resync is complete,
# attempt to bring DB _online, expected result _online will succeed, return status 200.
def test_bucket_online_offline_resync_with_online(num_users, num_docs, num_revisions):
    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset("resources/sync_gateway_configs/bucket_online_offline/db_online_offline_access_all_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log.info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
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
            log.info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log.error('User {} doc_id got revision {}, expected revision {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    restart_status = cluster.sync_gateways[0].restart("resources/sync_gateway_configs/bucket_online_offline/db_online_offline_access_restricted_cc.json")
    assert restart_status == 0

    log.info("Sleeping....")
    time.sleep(10)
    pool = ThreadPool(processes=1)

    log.info("Restarted SG....")
    time.sleep(5)

    db_info = admin.get_db_info("db")
    log.info("Status of db = {}".format(db_info["state"]))
    assert(db_info["state"] == "Offline")

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log.info("resync issued !!!!!!")
    except Exception as e:
        log.info("Catch resync exception: {}".format(e))

    time.sleep(1)
    resync_occured = False

    for i in range(20):
        db_info = admin.get_db_info("db")
        log.info("Status of db = {}".format(db_info["state"]))
        if db_info["state"] == "Resyncing":
            resync_occured = True
            log.info("Resync occured")
            try:
                status = admin.bring_db_online(db="db")
                log.info("online issued !!!!!online request status: {}".format(status))
            except HTTPError as e:
                log.info("status = {} exception = {}".format(status, e.response.status_code))
                if e.response.status_code == 503:
                    log.info("Got correct error code")
                else:
                    log.info("Got some other error failing test")
                    assert False

        time.sleep(1)
        if resync_occured:
            break

    time.sleep(10)

    status = admin.bring_db_online(db="db")
    log.info("online request issued !!!!! response status: {}".format(status))

    time.sleep(5)
    db_info = admin.get_db_info("db")
    log.info("Status of db = {}".format(db_info["state"]))
    assert (db_info["state"] == "Online")

    resync_result = async_resync_result.get()
    log.info("resync_changes {}".format(resync_result))
    log.info("expecting num_changes  == num_docs {} * num_users {}".format( num_docs, num_users))
    assert(resync_result['payload']['changes'] == num_docs * num_users)
    assert(resync_result['status_code'] == 200)

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    log.info("Test ended.")
    log.info("Main test duration: {}".format(end - init_completed))
    log.info("Test setup time: {}".format(init_completed - start))
    log.info("Total Time taken: {}s".format(end - start))


# implements scenario: 12 and 13
# While DB is running _resync make REST API calls against DB for supported offline operations,
# GET db status, PUT DB config, expected result calls should return status 200.
# #13
# With DB running a _resync, make REST API call to get DB runtime details /db/,
# expected result 'state' property with value 'Resyncing' is returned.
def test_bucket_online_offline_resync_with_offline(num_users, num_docs, num_revisions):
    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset("resources/sync_gateway_configs/bucket_online_offline/db_online_offline_access_all_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    num_channels = 1
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)
    user_x = admin.register_user(target=sgs[0], db="db", name="User-X", password="password", channels=["channel_x"])

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log.info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
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
            log.info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log.error('User {} doc_id got revision {}, expected revision {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in output.values()

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    restart_status = cluster.sync_gateways[0].restart("resources/sync_gateway_configs/bucket_online_offline/db_online_offline_access_restricted_cc.json")
    assert restart_status == 0

    log.info("Sleeping....")
    time.sleep(10)
    pool = ThreadPool(processes=1)

    log.info("Restarted SG....")
    time.sleep(5)

    db_info = admin.get_db_info("db")
    log.info("Status of db = {}".format(db_info["state"]))
    assert(db_info["state"] == "Offline")

    try:
        async_resync_result = pool.apply_async(admin.db_resync, ("db",))
        log.info("resync issued !!!!!!")
    except Exception as e:
        log.info("Catch resync exception: {}".format(e))

    time.sleep(1)
    resync_occured = False

    for i in range(20):
        db_info = admin.get_db_info("db")
        log.info("Status of db = {}".format(db_info["state"]))
        if db_info["state"] == "Resyncing":
            resync_occured = True
            log.info("Resync occured")
            try:
                status = admin.get_db_info(db="db")
                log.info("Got db_info request status: {}".format(status))
            except HTTPError as e:
                log.info("status = {} exception = {}".format(status, e.response.status_code))
                assert False
            else:
                log.info("Got 200 ok for supported operation")


        time.sleep(1)
        if resync_occured:
            break

    time.sleep(10)

    status = admin.bring_db_online(db="db")
    log.info("online request issued !!!!! response status: {}".format(status))

    time.sleep(5)
    db_info = admin.get_db_info("db")
    log.info("Status of db = {}".format(db_info["state"]))
    assert (db_info["state"] == "Online")

    resync_result = async_resync_result.get()
    log.info("resync_changes {}".format(resync_result))
    log.info("expecting num_changes  == num_docs {} * num_users {}".format( num_docs, num_users))
    assert(resync_result['payload']['changes'] == num_docs * num_users)
    assert(resync_result['status_code'] == 200)

    time.sleep(5)
    global_cache = list()
    for user in user_objects:
        global_cache.append(user.cache)

    all_docs = {k: v for user_cache in global_cache for k, v in user_cache.items()}

    verify_changes(user_x, expected_num_docs=expected_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    log.info("Test ended.")
    log.info("Main test duration: {}".format(end - init_completed))
    log.info("Test setup time: {}".format(init_completed - start))
    log.info("Total Time taken: {}s".format(end - start))
