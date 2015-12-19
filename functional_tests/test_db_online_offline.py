import pytest
import time
import concurrent.futures

from lib.admin import Admin
from lib.user import User
from lib.verify import verify_changes

import lib.settings

from requests.exceptions import HTTPError
from requests.exceptions import RetryError

from fixtures import cluster

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

NUM_ENDPOINTS = 11


def rest_scan(sync_gateway, db, online):

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
    # TODO: POST /{db}/_bulk_get

    # TODO: DELETE /{db}/{doc}
    # TODO: PUT /{db}/{doc}/{attachment}
    # TODO: GET /{db}/{doc}/{attachment}

    # Missing Local Document
    # TODO: PUT /{db}/{local-doc-id}
    # TODO: GET /{db}/{local-doc-id}
    # TODO: DELETE /{db}/{local-doc-id}

    # Missing Authentication
    # TODO: POST /{db}/_facebook_token
    # TODO: POST /{db}/_persona_assertion


    # Implement these
    # TODO: POST /{db}

    admin = Admin(sync_gateway=sync_gateway)

    error_responses = list()

    # PUT /{db}/_role/{name}
    try:
        admin.create_role(db=db, name="radio_stations", channels=["HWOD", "KDWB"])
    except HTTPError as e:
        status_code = e.response.status_code
        print "PUT _role exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/_role
    try:
        roles = admin.get_roles(db=db)
        print(roles)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _role exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/_role/{name}
    try:
        role = admin.get_role(db=db, name="radio_stations")
        print(role)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _role exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # PUT /{db}/_user/{name}
    try:
        seth = admin.register_user(target=sync_gateway, db=db, name="seth", password="password", channels=["FOX"])
    except HTTPError as e:
        status_code = e.response.status_code
        print "PUT _user exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/_user
    try:
        users_info = admin.get_users_info(db=db)
        print(users_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _user exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/_user/{name}
    try:
        user_info = admin.get_user_info(db=db, name="seth")
        print(user_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _user/<name> exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}
    try:
        db_info = admin.get_db_info(db=db)
        if not online:
            assert (db_info["state"] == "Offline")
        else:
            assert (db_info["state"] == "Online")
        print(db_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET / exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # Create dummy user to hit endpoint if offline, user creation above will fail
    if not online:
        seth = User(target=sync_gateway, db=db, name="seth", password="password", channels=["*", "ABC"])

    # PUT /{db}/{name}
    try:
        doc = seth.add_doc(doc_id="test-doc-1")
    except HTTPError as e:
        status_code = e.response.status_code
        print "add_doc or update_doc exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/{name}
    # PUT /{db}/{name}
    try:
        updated = seth.update_doc(doc_id="test-doc-1", num_revision=1)
    except HTTPError as e:
        status_code = e.response.status_code
        print "update_doc exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # POST /{db}/_bulk_docs
    try:
        docs = seth.add_bulk_docs(doc_ids=["test-doc-2", "test-doc-3"])
        updated = seth.update_doc(doc_id="test-doc-2", num_revision=1)
        updated = seth.update_doc(doc_id="test-doc-3", num_revision=1)
    except HTTPError as e:
        status_code = e.response.status_code
        print "bulk_doc exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # GET /{db}/_all_docs
    try:
        all_docs_result = seth.get_all_docs()
        print(all_docs_result)
        assert len(all_docs_result["rows"]) == 3
    except HTTPError as e:
        status_code = e.response.status_code
        print "get_all_docs exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    # wait for changes
    time.sleep(2)

    # GET /{db}/_changes
    try:
        changes = seth.get_changes()
        # If successful, verify the _changes feed
        verify_changes(seth, expected_num_docs=3, expected_num_revisions=1, expected_docs=seth.cache)
    except HTTPError as e:
        status_code = e.response.status_code
        print "get_all_docs exception: {}".format(status_code)
        error_responses.append((e.response.url, status_code))

    return error_responses


# Scenario 1
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
def test_online_default_rest(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
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
def test_offline_false_config_rest(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false.json")

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)

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
def test_online_to_offline_check_503(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")
    admin = Admin(cluster.sync_gateways[0])

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
    assert(len(errors) == 0)

    # Take bucket offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    # all db endpoints should return 503
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False)
    assert(len(errors) == NUM_ENDPOINTS)
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503)


# Scenario 5 - continuous
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize("num_docs", [5000])
def test_online_to_offline_changes_feed_controlled_close_continuous(cluster, num_docs):

    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")
    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])
    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_pusher", password="password", channels=["ABC"])

    docs_in_changes = dict()
    doc_add_errors = list()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        futures[executor.submit(seth.start_continuous_changes_tracking, termination_doc_id="killcontinuous")] = "continuous"
        futures[executor.submit(doc_pusher.add_docs, num_docs)] = "bulk_docs_push"
        time.sleep(5)
        futures[executor.submit(admin.take_db_offline, "db")] = "db_offline_task"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth continuous changes feed subscriber
                if task_name == "db_offline_task":
                    log.info("DB OFFLINE")
                    # make sure db_offline returns 200
                    assert(future.result() == 200)
                elif task_name == "bulk_docs_push":
                    log.info("DONE PUSHING DOCS")
                    doc_add_errors = future.result()
                elif task_name == "continuous":
                    docs_in_changes = future.result()
                    log.info("DOCS FROM CHANGES")
                    for k, v in docs_in_changes.items():
                        log.info("DFC -> {}:{}".format(k, v))

            except Exception as e:
                print("Futures: error: {}".format(e))

    print("Number of docs from _changes ({})".format(len(docs_in_changes)))
    print("Number of docs add errors ({})".format(len(doc_add_errors)))

    # TODO Discuss this pass criteria with dev
    # The less than num_docs ensures that the db was taken offline during doc pushes
    # docs_in_changes > 0 ensures that the connection closed and the continuous changes connection
    # returned the documents it had processed
    assert(len(docs_in_changes) > 20 and len(docs_in_changes) < num_docs)

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
    assert(num_docs_pushed + doc_add_errors == num_docs)


# Scenario 6 - longpoll
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
@pytest.mark.parametrize("num_docs", [5000])
def test_online_to_offline_changes_feed_controlled_close_longpoll(cluster, num_docs):

    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")
    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])
    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_pusher", password="password", channels=["ABC"])

    docs_in_changes = dict()
    doc_add_errors = list()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killpoll")] = "polling"
        futures[executor.submit(doc_pusher.add_docs, num_docs)] = "docs_push"
        time.sleep(5)
        futures[executor.submit(admin.take_db_offline, "db")] = "db_offline_task"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth continuous changes feed subscriber
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

    # TODO Discuss this pass criteria with dev
    # The less than num_docs ensures that the db was taken offline during doc pushes
    # docs_in_changes > 0 ensures that the connection closed and the continuous changes connection
    # returned the documents it had processed
    assert(len(docs_in_changes) > 20 and len(docs_in_changes) < num_docs)

    # TODO Why is this the case?
    # assert the last_seq_number == number _changes + 2 (_user doc starts and one and docs start at _user doc seq + 2)
    assert(len(docs_in_changes) + 2 == int(last_seq_num))

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
def test_offline_true_config_bring_online(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_offline_true.json")
    admin = Admin(cluster.sync_gateways[0])

    # all db endpoints should fail with 503
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False)

    assert(len(errors) == NUM_ENDPOINTS)
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503)

    # Scenario 9
    # POST /db/_online
    status = admin.bring_db_online(db="db")
    assert status == 200

    # all db endpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
    assert(len(errors) == 0)


# Scenario 14
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
def test_db_offline_TAP_loss_sanity(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")
    admin = Admin(cluster.sync_gateways[0])

    # all db rest enpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
    assert(len(errors) == 0)

    # Delete bucket to sever TAP feed
    cluster.servers[0].delete_bucket("data-bucket")

    # Check that bucket is in offline state
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False)
    assert(len(errors) == NUM_ENDPOINTS)
    for error_tuple in errors:
        print("({},{})".format(error_tuple[0], error_tuple[1]))
        assert(error_tuple[1] == 503)

# Scenario 16
@pytest.mark.sanity
@pytest.mark.dbonlineoffline
def test_config_change_invalid_1(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false.json")
    admin = Admin(cluster.sync_gateways[0])

    # all db endpoints should succeed
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
    assert(len(errors) == 0)

    config = admin.get_db_config(db="db")
    print(config)

    # Invalid config
    new_config = {
        "db": {
            "server": "http://{}:8091".format(cluster.servers[0].ip),
            "bucket": "data-bucket",
            "users": {
                "seth": {"password": "password", "admin_channels": ["*", "ABC"]},
                "Ashvinder": {"password": "password", "admin_channels": ["*", "CBS"]},
                "Andy": {"password": "password", "admin_channels": ["*", "NBC"]}
            }
        }
    }

    # VERIFY
    # Should status should be an error state?
    status = admin.put_db_config(db="db", config=new_config)
    assert(status == 201)

    # Take "db" offline
    status = admin.take_db_offline(db="db")
    assert(status == 200)

    # all db endpoints should 503
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=False)
    assert(len(errors) == NUM_ENDPOINTS)
    for error_tuple in errors:
        assert(error_tuple[1] == 503)

    # Bring "db" online
    # VERIFY - Correct status code
    status = admin.bring_db_online(db="db")
    assert(status == 500)
