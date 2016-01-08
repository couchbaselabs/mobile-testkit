import pytest
import time
import concurrent.futures
import uuid

from lib.admin import Admin
from lib.user import User
from lib.verify import verify_changes

import lib.settings

from requests.exceptions import HTTPError
from requests.exceptions import RetryError

from fixtures import cluster
from multiprocessing.pool import ThreadPool


import logging
log = logging.getLogger(lib.settings.LOGGER)

NUM_ENDPOINTS = 13

def rest_scan(sync_gateway, db, online, num_docs, user_name, channels):

    # Missing ADMIN
    # TODO: GET /{db}/_session/{session-id}
    # TODO: POST /{db}/_session
    # TODO: DELETE /{db}/_session/{session-id}
    # TODO: DELETE /{db}/_user/{name}/_session/{session-id}
    # TODO: DELETE /{db}/_user/{name}/_session

    # TODO: DELETE /{db}/_user/{name}

    # TODO: POST /{db}/_role/
    # TODO: DELETE /{db}/_role/{name}

    # Missing REST
    # TODO: POST /{db}/_all_docs

    # TODO: DELETE /{db}/{doc}
    # TODO: PUT /{db}/{doc}/{attachment}
    # TODO: GET /{db}/{doc}/{attachment}

    # Missing Local Document
    # TODO: DELETE /{db}/{local-doc-id}

    # Missing Authentication
    # TODO: POST /{db}/_facebook_token
    # TODO: POST /{db}/_persona_assertion

    admin = Admin(sync_gateway=sync_gateway)

    error_responses = list()

    # PUT /{db}/_role/{name}
    try:
        admin.create_role(db=db, name="radio_stations", channels=["HWOD", "KDWB"])
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/_role
    try:
        roles = admin.get_roles(db=db)
        print(roles)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/_role/{name}
    try:
        role = admin.get_role(db=db, name="radio_stations")
        print(role)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # PUT /{db}/_user/{name}
    try:
        user = admin.register_user(target=sync_gateway, db=db, name=user_name, password="password", channels=channels)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/_user
    try:
        users_info = admin.get_users_info(db=db)
        print(users_info)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/_user/{name}
    try:
        user_info = admin.get_user_info(db=db, name=user_name)
        print(user_info)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}
    try:
        db_info = admin.get_db_info(db=db)
        if not online:
            assert (db_info["state"] == "Offline")
        else:
            assert (db_info["state"] == "Online")
        print(db_info)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # Create dummy user to hit endpoint if offline, user creation above will fail
    if not online:
        user = User(target=sync_gateway, db=db, name=user_name, password="password", channels=channels)

    # PUT /{db}/{name}
    add_docs_errors = user.add_docs(num_docs=num_docs)
    error_responses.extend(add_docs_errors)

    # POST /{db}/_bulk_docs
    bulk_doc_errors = user.add_docs(num_docs=num_docs, bulk=True)
    error_responses.extend(bulk_doc_errors)

    # POST /{db}/
    for i in range(num_docs):
        try:
            user.add_doc()
        except HTTPError as e:
            log.error((e.response.url, e.response.status_code))
            error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/{name}
    # PUT /{db}/{name}
    if online:
        update_docs_errors = user.update_docs(num_revs_per_doc=1)
        error_responses.extend(update_docs_errors)
    else:
        try:
            # Try to hit the GET enpoint for "test-id"
            user.update_doc("test-id")
        except HTTPError as e:
            log.error((e.response.url, e.response.status_code))
            error_responses.append((e.response.url, e.response.status_code))

    # PUT /{db}/{local-doc-id}
    local_doc_id = uuid.uuid4()
    try:
        doc = user.add_doc("_local/{}".format(local_doc_id), content={"message": "I should not be replicated"})
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/{local-doc-id}
    try:
        doc = user.get_doc("_local/{}".format(local_doc_id))
        assert(doc["content"]["message"] == "I should not be replicated")
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # GET /{db}/_all_docs
    try:
        all_docs_result = user.get_all_docs()
        # num_docs /{db}/{doc} PUT + num_docs /{db}/_bulk_docs + num_docs POST /{db}/
        assert(len(all_docs_result["rows"]) == num_docs * 3)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # POST /{db}/_bulk_get
    try:
        doc_ids = list(user.cache.keys())
        first_ten_ids = doc_ids[:10]
        first_ten = user.get_docs(first_ten_ids)
        assert(len(first_ten) == 10)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    # wait for changes
    time.sleep(2)

    # GET /{db}/_changes
    try:
        changes = user.get_changes()
        # If successful, verify the _changes feed
        verify_changes(user, expected_num_docs=num_docs * 3, expected_num_revisions=1, expected_docs=user.cache)
    except HTTPError as e:
        log.error((e.response.url, e.response.status_code))
        error_responses.append((e.response.url, e.response.status_code))

    return error_responses


# Scenario 1
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_default_di.json", 100)
    ],
    ids=["CC-1", "DI-2"]
)
def test_online_default_rest(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == 0)

    # Scenario 4
    # Check the db has an Online state at each running sync_gateway
    for sg in cluster.sync_gateways:
        admin = Admin(sg)
        db_info = admin.get_db_info("db")
        assert (db_info["state"] == "Online")


# Scenario 2
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_offline_false_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_offline_false_di.json", 100)
    ],
    ids=["CC-1", "DI-2"]
)
def test_offline_false_config_rest(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])

    assert(len(errors) == 0)

    # Scenario 4
    # Check the db has an Online state at each running sync_gateway
    for sg in cluster.sync_gateways:
        admin = Admin(sg)
        db_info = admin.get_db_info("db")
        assert (db_info["state"] == "Online")


# Scenario 3
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_default_di.json", 100)
    ],
    ids=["CC-1", "DI-2"]
)
def test_online_to_offline_check_503(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)
    admin = Admin(cluster.sync_gateways[0])

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == 0)

    # Take bucket offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    # all db endpoints should return 503
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False, num_docs=num_docs, user_name="seth", channels=["ABC"])

    # We hit NUM_ENDPOINT unique REST endpoints + num of doc PUT failures
    assert(len(errors) == NUM_ENDPOINTS + (num_docs * 2))
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503)


# Scenario 5 - continuous
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 5000)
        #("bucket_online_offline/bucket_online_offline_default_di.json", 5000)
    ],
    ids=[
        "CC-1"
         #"DI-2"
        ]
)
def test_online_to_offline_changes_feed_controlled_close_continuous(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)
    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])
    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_pusher", password="password", channels=["ABC"])

    docs_in_changes = dict()
    doc_add_errors = list()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        futures[executor.submit(seth.start_continuous_changes_tracking, termination_doc_id=None)] = "continuous"
        futures[executor.submit(doc_pusher.add_docs, num_docs)] = "docs_push"
        time.sleep(5)
        futures[executor.submit(admin.take_db_offline, "db")] = "db_offline_task"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                if task_name == "db_offline_task":
                    log.info("DB OFFLINE")
                    # make sure db_offline returns 200
                    assert(future.result() == 200)
                elif task_name == "docs_push":
                    log.info("DONE PUSHING DOCS")
                    doc_add_errors = future.result()
                elif task_name == "continuous":
                    docs_in_changes = future.result()
                    log.info("DOCS FROM CHANGES")
                    for k, v in docs_in_changes.items():
                        log.info("DFC -> {}:{}".format(k, v))

            except Exception as e:
                print("Futures: error: {}".format(e))

    log.info("Number of docs from _changes ({})".format(len(docs_in_changes)))
    log.info("Number of docs add errors ({})".format(len(doc_add_errors)))

    # Some docs should have made it to _changes
    assert(len(docs_in_changes) > 0)

    # Bring db back online
    status = admin.bring_db_online("db")
    assert(status == 200)

    # Get all docs that have been pushed
    # Verify that changes returns all of them
    all_docs = doc_pusher.get_all_docs()
    num_docs_pushed = len(all_docs["rows"])
    verify_changes(doc_pusher, expected_num_docs=num_docs_pushed, expected_num_revisions=0, expected_docs=doc_pusher.cache)

    # Check that the number of errors return when trying to push while db is offline + num of docs in db
    # should equal the number of docs
    assert(num_docs_pushed + len(doc_add_errors) == num_docs)


# Scenario 6 - longpoll
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 5000),
        ("bucket_online_offline/bucket_online_offline_default_di.json", 5000)
    ],
    ids=["CC-1", "DI-2"]
)
def test_online_to_offline_changes_feed_controlled_close_longpoll_sanity(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        # start longpoll tracking with no timeout, will block until longpoll is closed by db going offline
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id=None, timeout=0, loop=False)] = "polling"
        time.sleep(5)
        futures[executor.submit(admin.take_db_offline, "db")] = "db_offline_task"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                if task_name == "db_offline_task":
                    log.info("DB OFFLINE")
                    # make sure db_offline returns 200
                    assert(future.result() == 200)
                if task_name == "polling":
                    # Long poll will exit with 503, return docs in the exception
                    log.info("POLLING DONE")
                    try:
                        docs_in_changes, last_seq_num = future.result()
                    except Exception as e:
                        log.error("Longpoll feed close error: {}".format(e))
                        # long poll should be closed so this exception should never happen
                        assert(0)

            except Exception as e:
                print("Futures: error: {}".format(e))

    # Account for _user doc
    # last_seq may be of the form '1' for channel cache or '1-0' for distributed index
    seq_num_component = last_seq_num.split("-")
    assert(1 == int(seq_num_component[0]))
    assert(len(docs_in_changes) == 0)


# Scenario 6 - longpoll
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 5000)
        #("bucket_online_offline/bucket_online_offline_default_di.json", 5000)
    ],
    ids=[
        "CC-1"
        #"DI-2"
    ]
)
def test_online_to_offline_changes_feed_controlled_close_longpoll(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])
    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_pusher", password="password", channels=["ABC"])

    docs_in_changes = dict()
    doc_add_errors = list()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id=None)] = "polling"
        futures[executor.submit(doc_pusher.add_docs, num_docs)] = "docs_push"
        time.sleep(5)
        futures[executor.submit(admin.take_db_offline, "db")] = "db_offline_task"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                if task_name == "db_offline_task":
                    log.info("DB OFFLINE")
                    # make sure db_offline returns 200
                    assert(future.result() == 200)
                if task_name == "docs_push":
                    log.info("DONE PUSHING DOCS")
                    doc_add_errors = future.result()
                if task_name == "polling":
                    # Long poll will exit with 503, return docs in the exception
                    log.info("POLLING DONE")
                    try:
                        docs_in_changes = future.result()
                    except Exception as e:
                        log.info(e)
                        log.info("POLLING DONE EXCEPTION")
                        log.info("AARGS: {}".format(e.args))
                        docs_in_changes = e.args[0]["docs"]
                        last_seq_num = e.args[0]["last_seq_num"]
                        log.info("DOCS FROM longpoll")
                        for k, v in docs_in_changes.items():
                            log.info("DFC -> {}:{}".format(k, v))
                        log.info("LAST_SEQ_NUM FROM longpoll {}".format(last_seq_num))

            except Exception as e:
                print("Futures: error: {}".format(e))

    log.info("Number of docs from _changes ({})".format(len(docs_in_changes)))
    log.info("last_seq_num _changes ({})".format(last_seq_num))
    log.info("Number of docs add errors ({})".format(len(doc_add_errors)))

    # Some docs should have made it to _changes
    assert(len(docs_in_changes) > 0)

    seq_num_component = last_seq_num.split("-")

    # last_seq may be of the form '1' for channel cache or '1-0' for distributed index
    # assert the last_seq_number == number _changes + 2 (_user doc starts and one and docs start at _user doc seq + 2)
    seq_num_component = last_seq_num.split("-")
    assert(len(docs_in_changes) + 2 == int(seq_num_component[0]))

    # Bring db back online
    status = admin.bring_db_online("db")
    assert(status == 200)
    #
    # Get all docs that have been pushed
    # Verify that changes returns all of them
    all_docs = doc_pusher.get_all_docs()
    num_docs_pushed = len(all_docs["rows"])
    verify_changes(doc_pusher, expected_num_docs=num_docs_pushed, expected_num_revisions=0, expected_docs=doc_pusher.cache)

    # Check that the number of errors return when trying to push while db is offline + num of docs in db
    # should equal the number of docs
    assert(num_docs_pushed + len(doc_add_errors) == num_docs)


# Scenario 6
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_offline_true_cc.json", 100),
        #("bucket_online_offline/bucket_online_offline_offline_true_di.json", 100)
    ],
    ids=[
        "CC-1"
    #    "DI-2"
    ]
)
def test_offline_true_config_bring_online(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    admin = Admin(cluster.sync_gateways[0])

    # all db endpoints should fail with 503
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False, num_docs=num_docs, user_name="seth", channels=["ABC"])

    assert(len(errors) == NUM_ENDPOINTS + (num_docs * 2))
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503)

    # Scenario 9
    # POST /db/_online
    status = admin.bring_db_online(db="db")
    assert status == 200

    # all db endpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == 0)


# Scenario 14
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_dcp_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_default_di.json", 100)
    ],
    ids=["CC-1", "CC-2", "DI-3"]
)
def test_db_offline_tap_loss_sanity(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    admin = Admin(cluster.sync_gateways[0])

    # all db rest enpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == 0)

    # Delete bucket to sever TAP feed
    cluster.servers[0].delete_bucket("data-bucket")

    # Check that bucket is in offline state
    # Will return 401 for public enpoint because the auth doc has been deleted
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == NUM_ENDPOINTS + (num_docs * 2))
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503 or error_tuple[1] == 401)

# Scenario 11
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_default_cc.json", 100),
        #("bucket_online_offline/bucket_online_offline_default_di.json", 100)
    ],
    ids=[
        "CC-1"
         #"DI-2"
         ]
)
def test_db_delayed_online(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    admin = Admin(cluster.sync_gateways[0])

    time.sleep(2)
    status = admin.take_db_offline("db")
    log.info("offline request response status: {}".format(status))
    time.sleep(10)

    pool = ThreadPool(processes=1)

    db_info = admin.get_db_info("db")
    assert (db_info["state"] == "Offline")

    async_result = pool.apply_async(admin.bring_db_online, ("db", 15,))
    status = async_result.get(timeout=15)
    log.info("offline request response status: {}".format(status))

    time.sleep(20)

    db_info = admin.get_db_info("db")
    assert (db_info["state"] == "Online")

    # all db rest enpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
    assert(len(errors) == 0)



@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_cc.json", 100),
        ("bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_di.json", 100)
    ],
    ids=["CC-1", "DI-2"]
)
def test_multiple_dbs_unique_buckets_lose_tap(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)

    dbs = ["db1", "db2", "db3", "db4"]

    # all db rest endpoints should succeed
    for db in dbs:
        errors = rest_scan(cluster.sync_gateways[0], db=db, online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
        assert(len(errors) == 0)

    cluster.servers[0].delete_bucket("data-bucket-1")
    cluster.servers[0].delete_bucket("data-bucket-3")

    # Check that db2 and db4 are still Online
    for db in ["db2", "db4"]:
        errors = rest_scan(cluster.sync_gateways[0], db=db, online=True, num_docs=num_docs, user_name="adam", channels=["CBS"])
        assert(len(errors) == 0)

    # Check that db1 and db3 go offline
    for db in ["db1", "db3"]:
        errors = rest_scan(cluster.sync_gateways[0], db=db, online=False, num_docs=num_docs, user_name="seth", channels=["ABC"])
        assert(len(errors) == NUM_ENDPOINTS + (num_docs * 2))
        for error_tuple in errors:
            print("({},{})".format(error_tuple[0], error_tuple[1]))
            assert(error_tuple[1] == 503 or error_tuple[1] == 401)


# Reenable for 1.3
# Scenario 16
# @pytest.mark.sanity
# @pytest.mark.dbonlineoffline
# @pytest.mark.parametrize(
#     "num_docs",
#     [100]
# )
# def test_config_change_invalid_1(cluster, num_docs):
#
#     cluster.reset("bucket_online_offline/bucket_online_offline_offline_false_cc.json")
#     admin = Admin(cluster.sync_gateways[0])
#
#     # all db endpoints should succeed
#     errors = rest_scan(cluster.sync_gateways[0], db="db", online=True, num_docs=num_docs, user_name="seth", channels=["ABC"])
#     assert(len(errors) == 0)
#
#     config = admin.get_db_config(db="db")
#     print(config)
#
#     # Invalid config
#     new_config = {
#         "db": {
#             "server": "http://{}:8091".format(cluster.servers[0].ip),
#             "bucket": "data-bucket",
#             "users": {
#                 "seth": {"password": "password", "admin_channels": ["*", "ABC"]},
#                 "Ashvinder": {"password": "password", "admin_channels": ["*", "CBS"]},
#                 "Andy": {"password": "password", "admin_channels": ["*", "NBC"]}
#             }
#         }
#     }
#
#     # VERIFY
#     # Should status should be an error state?
#     status = admin.put_db_config(db="db", config=new_config)
#     assert(status == 201)
#
#     # Take "db" offline
#     status = admin.take_db_offline(db="db")
#     assert(status == 200)
#
#     # all db endpoints should 503
#     errors = rest_scan(cluster.sync_gateways[0], db="db", online=False, num_docs=num_docs, user_name="seth", channels=["ABC"])
#     assert(len(errors) == NUM_ENDPOINTS + num_docs)
#     for error_tuple in errors:
#         assert(error_tuple[1] == 503)
#
#     # Bring "db" online
#     # VERIFY - Correct status code
#     status = admin.bring_db_online(db="db")
#     assert(status == 500)


## Scenario 17
#@pytest.mark.dbonlineoffline
#def test_db_online_offline_with_invalid_legal_config(cluster, disable_http_retry):
#    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false_cc.json")
#    admin = Admin(cluster.sync_gateways[0])
#
#    # all db endpoints should succeed
#    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
#    assert(len(errors) == 0)
#
#    #restart_status = cluster.sync_gateways[0].restart("bucket_online_offline/db_online_offline_invalid_db_cc.json")
#    #assert restart_status == 0
#
#    config = admin.get_db_config(db="db")
#    print(config)
#
#    # Invalid config
#    new_config = {
#        "db": {
#            "server": "http://{}:8091".format(cluster.servers[0].ip),
#            "bucket": "data-bucket",
#            "users": {
#                "seth": {"password": "password", "admin_channels": ["*", "ABC"]},
#                "Ashvinder": {"password": "password", "admin_channels": ["*", "CBS"]},
#                "Andy": {"password": "password", "admin_channels": ["*", "NBC"]}
#            }
#        }
#    }
#
#    status = admin.put_db_config(db="db", config=new_config)
#    assert(status == 201)
#
#    # Take "db" offline
#    status = admin.bring_db_online(db="db")
#    log.info("status: {}".format(status))
#    assert(status == 200)
#
#
#
