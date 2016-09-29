import json
import re
import time
import pytest

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import SyncGateway


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
@pytest.mark.parametrize("continuous", [
    True,
    False
])
def test_initial_pull_replication(setup_client_syncgateway_test, continuous):
    """
    1. Prepare sync-gateway to have 10000 documents.
    2. Create a single shot / continuous pull replicator and to pull the docs into a database.
    3. Verify if all of the docs get pulled.
    Referenced issue: couchbase/couchbase-lite-android#955.
    """

    sg_db = "db"
    ls_db = "ls_db"

    num_docs = 10000

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_one_public,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_initial_pull_replication', continuous: {}".format(continuous))
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_user(sg_one_admin, sg_db, "seth", password="password", channels=["ABC", "NBC"])
    session = client.create_session(sg_one_admin, sg_db, "seth")

    # Create 'num_docs' docs on sync_gateway
    docs = client.add_docs(
        url=sg_one_public,
        db=sg_db,
        number=num_docs,
        id_prefix="seeded_doc",
        generator="four_k",
        auth=session
    )

    client.create_database(url=ls_url, name=ls_db)

    # Start oneshot pull replication
    repl_id = client.start_replication(
        url=ls_url,
        continuous=continuous,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db
    )

    start = time.time()

    if continuous:
        log_info("Waiting for replication status 'Idle' for: {}".format(repl_id))
        # Android will report IDLE status, and drop into the 'verify_docs_present' below
        # due to https://github.com/couchbase/couchbase-lite-java-core/issues/1409
        client.wait_for_replication_status_idle(ls_url, repl_id)
    else:
        log_info("Waiting for no replications".format(repl_id))
        client.wait_for_no_replications(ls_url)

    # Verify docs replicated to client
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs, timeout=240)

    all_docs_replicated_time = time.time() - start
    log_info("Replication took: {}s".format(all_docs_replicated_time))

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=ls_url, db=ls_db, expected_docs=docs)

    replications = client.get_replications(url=ls_url)

    if continuous:
        assert len(replications) == 1, "There should only be one replication running"
        assert replications[0]["status"] == "Idle", "Replication Status should be 'Idle'"
        assert replications[0]["continuous"], "Running replication should be continuous"
        # Only .NET has an 'error' property
        if "error" in replications[0]:
            assert len(replications[0]["error"]) == 0
    else:
        assert len(replications) == 0, "No replications should be running"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
@pytest.mark.parametrize("continuous", [
    True,
    False
])
def test_initial_push_replication(setup_client_syncgateway_test, continuous):
    """
    1. Prepare LiteServ to have 10000 documents.
    2. Create a single shot push / continuous replicator and to push the docs into a sync_gateway database.
    3. Verify if all of the docs get pushed.
    """

    sg_db = "db"
    ls_db = "ls_db"
    seth_channels = ["ABC", "NBC"]

    num_docs = 10000

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_one_public,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_initial_push_replication', continuous: {}".format(continuous))
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_user(sg_one_admin, sg_db, "seth", password="password", channels=seth_channels)
    session = client.create_session(sg_one_admin, sg_db, "seth")

    client.create_database(url=ls_url, name=ls_db)

    # Create 'num_docs' docs on LiteServ
    docs = client.add_docs(
        url=ls_url,
        db=ls_db,
        number=num_docs,
        id_prefix="seeded_doc",
        generator="four_k",
        channels=seth_channels
    )

    # Start push replication
    repl_id = client.start_replication(
        url=ls_url,
        continuous=continuous,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db
    )

    if continuous:
        log_info("Waiting for replication status 'Idle' for: {}".format(repl_id))
        client.wait_for_replication_status_idle(ls_url, repl_id)
    else:
        log_info("Waiting for no replications".format(repl_id))
        client.wait_for_no_replications(ls_url)

    # Verify docs replicated to sync_gateway
    client.verify_docs_present(url=sg_one_public, db=sg_db, expected_docs=docs, auth=session)

    # Verify docs show up in sync_gateway's changes feed
    client.verify_docs_in_changes(url=sg_one_public, db=sg_db, expected_docs=docs, auth=session)

    replications = client.get_replications(url=ls_url)

    if continuous:
        assert len(replications) == 1, "There should only be one replication running"
        assert replications[0]["status"] == "Idle", "Replication Status should be 'Idle'"
        assert replications[0]["continuous"], "Running replication should be continuous"
        # Only .NET has an 'error' property
        if "error" in replications[0]:
            assert len(replications[0]["error"]) == 0
    else:
        assert len(replications) == 0, "No replications should be running"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_multiple_replications_not_created_with_same_properties(setup_client_syncgateway_test):
    """Regression test for https://github.com/couchbase/couchbase-lite-android/issues/939
    1. Create LiteServ database and launch sync_gateway with database
    2. Start 5 continuous push replicators with the same source and target
    3. Make sure the sample replication id is returned
    4. Check that 1 one replication exists in 'active_tasks'
    5. Stop the replication with POST /_replicate cancel=true
    6. Start 5 continuous pull replicators with the same source and target
    7. Make sure the sample replication id is returned
    8. Check that 1 one replication exists in 'active_tasks'
    9. Stop the replication with POST /_replicate cancel=true
    """

    sg_db = "db"
    ls_db = "ls_db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_one_public,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_multiple_replications_not_created_with_same_properties'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)

    repl_id_num = 0
    response_one_id_num = 0
    response_two_id_num = 0

    # launch 50 concurrent push replication requests with the same source / target
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(
            client.start_replication,
            url=ls_url,
            continuous=True,
            from_db=ls_db,
            to_url=sg_one_admin,
            to_db=sg_db
        ) for _ in range(50)]

        for future in as_completed(futures):
            response_one_id = future.result()
            # Convert session_id from string "repl001" -> int 1
            response_one_id_num = int(response_one_id.replace("repl", ""))
            log_info(response_one_id_num)

    # Assert that concurrent replications have a greater session id than 0
    assert response_one_id_num > repl_id_num, "'response_one_id_num': {} should be greater than 'repl_id_num': {}".format(
        response_one_id_num,
        repl_id_num
    )

    # Check there is only one replication running
    replications = client.get_replications(ls_url)
    assert len(replications) == 1, "Number of replications, Expected: {} Actual {}".format(
        1,
        len(replications)
    )

    # Stop replication
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db
    )

    # Check that no replications are running
    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual {}".format(
        0,
        len(replications)
    )

    # launch 50 concurrent pull replication requests with the same source / target
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(
            client.start_replication,
            url=ls_url,
            continuous=True,
            from_db=sg_db,
            from_url=sg_one_admin,
            to_db=ls_db
        ) for _ in range(50)]

        for future in as_completed(futures):
            response_two_id = future.result()
            # Convert session_id from string "repl001" -> int 1
            response_two_id_num = int(response_two_id.replace("repl", ""))
            log_info(response_two_id_num)

    # Assert that the second set of concurrent replication requests has a higher id than the first
    assert response_two_id_num > response_one_id_num, "'response_two_id_num': {} should be greater than 'response_one_id_num': {}".format(
        response_two_id_num,
        response_one_id_num
    )

    # Check there is only one replication running
    replications = client.get_replications(ls_url)
    assert len(replications) == 1, "Number of replications, Expected: {} Actual {}".format(
        1,
        len(replications)
    )

    # Stop replication
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=sg_db,
        from_url=sg_one_admin,
        to_db=ls_db
    )

    # Check that no replications are running
    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual {}".format(
        0,
        len(replications)
    )


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_multiple_replications_created_with_unique_properties(setup_client_syncgateway_test):
    """Regression test for couchbase/couchbase-lite-java-core#1386
    1. Setup SGW with a remote database name db for an example
    2. Create a local database such as ls_db
    3. Send POST /_replicate with source = ls_db, target = http://localhost:4985/db, continuous = true
    4. Send POST /_replicate with source = ls_db, target = http://localhost:4985/db, continuous = true, doc_ids=["doc1", "doc2"]
    5. Send POST /_replicate with source = ls_db, target = http://localhost:4985/db, continuous = true, filter="filter1"
    6. Make sure that the session_id from each POST /_replicate are different.
    7. Send GET /_active_tasks to make sure that there are 3 tasks created.
    8. Send 3 POST /_replicate withe the same parameter as Step 3=5 plus cancel=true to stop those replicators
    9. Repeat Step 3 - 8 with source = and target = db for testing the pull replicator.
    """

    sg_db = "db"
    ls_db = "ls_db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_one_public,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_multiple_replications_created_with_unique_properties'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)

    ########
    # PUSH #
    ########
    # Start 3 unique push replication requests
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db
    )
    client.wait_for_replication_status_idle(ls_url, repl_one)

    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db,
        doc_ids=["doc_1", "doc_2"]
    )
    client.wait_for_replication_status_idle(ls_url, repl_two)

    # Create doc filter and add to the design doc
    filters = {
        "language": "javascript",
        "filters": {
            "sample_filter": "function(doc, req) { if (doc.type && doc.type === \"skip\") { return false; } return true; }"
        }
    }
    client.add_design_doc(url=ls_url, db=ls_db, name="by_type", doc=json.dumps(filters))

    repl_three = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db,
        repl_filter="by_type/sample_filter"
    )
    client.wait_for_replication_status_idle(ls_url, repl_three)

    # Verify 3 replicaitons are running
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 3, "Number of replications, Expected: {} Actual: {}".format(
        3,
        len(replications)
    )

    # Stop repl001
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db
    )

    # Stop repl002
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db,
        doc_ids=["doc_1", "doc_2"]
    )

    # Stop repl003
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db,
        repl_filter="by_type/sample_filter"
    )

    # Verify no replications are running
    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual: {}".format(
        0,
        len(replications)
    )

    ########
    # PULL #
    ########
    # Start 3 unique push replication requests
    repl_four = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db
    )
    client.wait_for_replication_status_idle(ls_url, repl_four)

    # Start filtered pull from sync gateway to LiteServ
    repl_five = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db,
        channels_filter=["ABC", "CBS"]
    )
    client.wait_for_replication_status_idle(ls_url, repl_five)

    # Verify 3 replicaitons are running
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 2, "Number of replications, Expected: {} Actual: {}".format(
        2,
        len(replications)
    )

    # Stop repl_four
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db
    )

    # Stop repl_five
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db,
        channels_filter=["ABC", "CBS"]
    )

    # Verify no replications are running
    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual: {}".format(
        0,
        len(replications)
    )


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.sessions
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_replication_with_session_cookie(setup_client_syncgateway_test):
    """Regression test for https://github.com/couchbase/couchbase-lite-android/issues/817
    1. SyncGateway Config with guest disabled = true and One user added (e.g. user1 / 1234)
    2. Create a new session on SGW for the user1 by using POST /_session.
       Capture the SyncGatewaySession cookie from the set-cookie in the response header.
    3. Start continuous push and pull replicator on the LiteServ with SyncGatewaySession cookie.
       Make sure that both replicators start correctly
    4. Delete the session from SGW by sending DELETE /_sessions/ to SGW
    5. Cancel both push and pull replicator on the LiteServ
    6. Repeat step 1 and 2
    """

    ls_db = "ls_db"
    sg_db = "db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_url,
        config="{}/walrus-user.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_replication_with_session_cookie'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)

    # Get session header for user_1
    session_header = client.create_session_header(url=sg_url, db=sg_db, name="user_1", password="foo")

    # Get session id from header
    session_parts = re.split("=|;", session_header)
    session_id = session_parts[1]
    log_info("{}: {}".format(session_parts[0], session_id))
    session = (session_parts[0], session_id)

    # Start authenticated push replication
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_url,
        to_db=sg_db,
        to_auth=session_header
    )

    # Start authenticated pull replication
    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url,
        from_db=sg_db,
        from_auth=session_header,
        to_db=ls_db,
    )

    # Wait for 2 replications to be 'Idle', On .NET they may not be immediately available via _active_tasks
    client.wait_for_replication_status_idle(ls_url, repl_one)
    client.wait_for_replication_status_idle(ls_url, repl_two)

    replications = client.get_replications(ls_url)
    assert len(replications) == 2, "2 replications (push / pull should be running)"

    # Sanity test docs
    ls_docs = client.add_docs(url=ls_url, db=ls_db, number=100, id_prefix="ls_doc", channels=["ABC"])
    sg_docs = client.add_docs(url=sg_url, db=sg_db, number=100, id_prefix="sg_doc", auth=session, channels=["ABC"])
    all_docs = client.merge(ls_docs, sg_docs)
    log_info(all_docs)

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=all_docs)
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=all_docs)

    # GET from session endpoint /{db}/_session/{session-id}
    session = client.get_session(url=sg_admin_url, db=sg_db, session_id=session_id)
    assert len(session["userCtx"]["channels"]) == 2, "There should be only 2 channels for the user"
    assert "ABC" in session["userCtx"]["channels"], "The channel info should contain 'ABC'"
    assert session["userCtx"]["name"] == "user_1", "The user should have the name 'user_1'"
    assert len(session["authentication_handlers"]) == 2, "There should be 2 authentication_handlers"
    assert "default" in session["authentication_handlers"], "Did not find 'default' in authentication_headers"
    assert "cookie" in session["authentication_handlers"], "Did not find 'cookie' in authentication_headers"

    log_info("SESSIONs: {}".format(session))

    # Delete session via sg admin port and _user rest endpoint
    client.delete_session(url=sg_admin_url, db=sg_db, user_name="user_1", session_id=session_id)

    # Make sure session is deleted
    try:
        session = client.get_session(url=sg_admin_url, db=sg_db, session_id=session_id)
    except HTTPError as he:
        expected_error_code = he.response.status_code
        log_info(expected_error_code)

    assert expected_error_code == 404, "Expected 404 status, actual {}".format(expected_error_code)

    # Cancel the replications
    # Stop repl_one
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_url,
        to_db=sg_db,
        to_auth=session_header
    )

    # Stop repl_two
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url,
        from_db=sg_db,
        from_auth=session_header,
        to_db=ls_db,
    )

    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "All replications should be stopped"

    # Create new session and new push / pull replications
    session_header = client.create_session_header(url=sg_url, db=sg_db, name="user_1", password="foo")

    # Get session id from header
    session_parts = re.split("=|;", session_header)
    session_id = session_parts[1]
    log_info("{}: {}".format(session_parts[0], session_id))

    # Start authenticated push replication
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_url,
        to_db=sg_db,
        to_auth=session_header
    )

    # Start authenticated pull replication
    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url,
        from_db=sg_db,
        from_auth=session_header,
        to_db=ls_db,
    )

    replications = client.get_replications(ls_url)
    assert len(replications) == 2, "2 replications (push / pull should be running), found: {}".format(2)

    session = client.get_session(url=sg_admin_url, db=sg_db, session_id=session_id)
    assert len(session["userCtx"]["channels"]) == 2, "There should be only 2 channels for the user"
    assert "ABC" in session["userCtx"]["channels"], "The channel info should contain 'ABC'"
    assert session["userCtx"]["name"] == "user_1", "The user should have the name 'user_1'"
    assert len(session["authentication_handlers"]) == 2, "There should be 2 authentication_handlers"
    assert "default" in session["authentication_handlers"], "Did not find 'default' in authentication_headers"
    assert "cookie" in session["authentication_handlers"], "Did not find 'cookie' in authentication_headers"

    log_info("SESSIONs: {}".format(session))

    # Delete session via sg admin port and db rest endpoint
    client.delete_session(url=sg_admin_url, db=sg_db, session_id=session_id)

    # Make sure session is deleted
    try:
        session = client.get_session(url=sg_admin_url, db=sg_db, session_id=session_id)
    except HTTPError as he:
        expected_error_code = he.response.status_code
        log_info(expected_error_code)

    assert expected_error_code == 404, "Expected 404 status, actual {}".format(expected_error_code)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.compaction
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_client_to_sync_gateway_complex_replication_with_revs_limit(setup_client_syncgateway_test):
    """ Ported from sync_gateway tests repo
    ...  1.  Clear server buckets
    ...  2.  Restart liteserv with _session
    ...  3.  Restart sync_gateway wil that config
    ...  4.  Create db on LiteServ
    ...  5.  Add numDocs to LiteServ db
    ...  6.  Setup push replication from LiteServ db to sync_gateway
    ...  7.  Verify doc present on sync_gateway (number of docs)
    ...  8.  Update sg docs numRevs * 4 = 480
    ...  9.  Update docs on LiteServ db numRevs * 4 = 480
    ...  10. Setup pull replication from sg -> liteserv db
    ...  11. Verify all docs are replicated
    ...  12. compact LiteServ db (POST _compact)
    ...  13. Verify number of revs in LiteServ db (?revs_info=true) check rev status == available fail if revs available > revs limit
    ...  14. Delete LiteServ db conflicts (?conflicts=true) DELETE _conflicts
    ...  15. Create numDoc number of docs in LiteServ db
    ...  16. Update LiteServ db docs numRevs * 5 (600)
    ...  17. Verify LiteServ db revs is < 602
    ...  18. Verify LiteServ db docs revs prefix (9 * numRevs + 3)
    ...  19. Compact LiteServ db
    ...  20. Verify number of revs <= 10
    ...  21. Delete LiteServ docs
    ...  22. Delete Server bucket
    ...  23. Delete LiteServ db
    """

    ls_db_name = "ls_db"
    sg_db = "db"
    sg_user_name = "sg_user"
    num_docs = 10
    num_revs = 100

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_url,
        config="{}/walrus-revs-limit.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_client_to_sync_gateway_complex_replication_with_revs_limit'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()

    # Test the endpoint, listener does not support users but should have a default response
    client.get_session(url=ls_url)

    sg_user_channels = ["NBC"]
    client.create_user(url=sg_admin_url, db=sg_db, name=sg_user_name, password="password", channels=sg_user_channels)
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)

    ls_db = client.create_database(url=ls_url, name=ls_db_name)
    ls_db_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs, id_prefix=ls_db, channels=sg_user_channels)

    # Start replication ls_db -> sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_db_docs)

    # Delay is to the updates here due to couchbase/couchbase-lite-ios#1277.
    # Basically, if your revs depth is small and someone is updating a doc past the revs depth before a push replication,
    # the push replication will have no common ancestor with sync_gateway causing conflicts to be created.
    # Adding a delay between updates helps this situation. There is an alternative for CBL mac and CBL NET to change the default revs client depth
    # but that is not configurable for Android.
    # Currently adding a delay will allow the replication to act as expected for all platforms now.
    client.update_docs(url=sg_url, db=sg_db, docs=ls_db_docs, number_updates=num_revs, delay=0.1, auth=sg_session)
    client.update_docs(url=ls_url, db=ls_db, docs=ls_db_docs, number_updates=num_revs, delay=0.1)

    # Start replication ls_db <- sg_db
    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db
    )

    client.wait_for_replication_status_idle(url=ls_url, replication_id=repl_one)
    client.wait_for_replication_status_idle(url=ls_url, replication_id=repl_two)

    client.compact_database(url=ls_url, db=ls_db)

    # LiteServ should only have 20 revisions due to built in client revs limit
    client.verify_revs_num_for_docs(url=ls_url, db=ls_db, docs=ls_db_docs, expected_revs_per_doc=20)

    # Sync Gateway should have 100 revisions due to the specified revs_limit in the sg config and possible conflict winners from the liteserv db
    client.verify_max_revs_num_for_docs(url=sg_url, db=sg_db, docs=ls_db_docs, expected_max_number_revs_per_doc=100, auth=sg_session)

    client.delete_conflicts(url=ls_url, db=ls_db, docs=ls_db_docs)
    expected_generation = num_revs + 1
    client.verify_docs_rev_generations(url=ls_url, db=ls_db, docs=ls_db_docs, expected_generation=expected_generation)
    client.verify_docs_rev_generations(url=sg_url, db=sg_db, docs=ls_db_docs, expected_generation=expected_generation, auth=sg_session)

    client.delete_docs(url=ls_url, db=ls_db, docs=ls_db_docs)
    client.verify_docs_deleted(url=ls_url, db=ls_db, docs=ls_db_docs)
    client.verify_docs_deleted(url=sg_admin_url, db=sg_db, docs=ls_db_docs)

    ls_db_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs, id_prefix=ls_db, channels=sg_user_channels)
    expected_revs = num_revs + 20 + 2
    client.update_docs(url=ls_url, db=ls_db, docs=ls_db_docs, delay=0.1, number_updates=num_revs)

    client.verify_max_revs_num_for_docs(url=ls_url, db=ls_db, docs=ls_db_docs, expected_max_number_revs_per_doc=expected_revs)

    expected_generation = (num_revs * 2) + 3
    client.verify_docs_rev_generations(url=ls_url, db=ls_db, docs=ls_db_docs, expected_generation=expected_generation)

    client.compact_database(url=ls_url, db=ls_db)
    client.verify_revs_num_for_docs(url=ls_url, db=ls_db, docs=ls_db_docs, expected_revs_per_doc=20)

    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db
    )

    client.wait_for_no_replications(url=ls_url)

    client.delete_conflicts(url=ls_url, db=ls_db, docs=ls_db_docs)
    client.delete_conflicts(url=sg_url, db=sg_db, docs=ls_db_docs, auth=sg_session)
    client.delete_docs(url=ls_url, db=ls_db, docs=ls_db_docs)

    # Start push pull and verify that all docs are deleted
    # Start replication ls_db -> sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    # Start replication ls_db <- sg_db
    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db
    )

    client.verify_docs_deleted(url=ls_url, db=ls_db, docs=ls_db_docs)
    client.verify_docs_deleted(url=sg_admin_url, db=sg_db, docs=ls_db_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_replication_with_multiple_client_dbs_and_single_sync_gateway_db(setup_client_syncgateway_test):
    """Test replication from multiple client dbs to one sync_gateway db"""

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    num_docs = 1000

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_url,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_replication_with_multiple_client_dbs_and_single_sync_gateway_db'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()

    ls_db1 = client.create_database(url=ls_url, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url, name="ls_db2")
    sg_db = client.create_database(url=sg_admin_url, name="sg_db", server="walrus:")

    # Setup continuous push / pull replication from ls_db1 to sg_db
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db1,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db1
    )

    # Setup continuous push / pull replication from ls_db2 to sg_db
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db2,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db2
    )

    ls_db_one_docs = client.add_docs(url=ls_url, db=ls_db1, number=num_docs, id_prefix=ls_db1)
    ls_db_two_docs = client.add_docs(url=ls_url, db=ls_db2, number=num_docs, id_prefix=ls_db2)

    ls_db1_db2_docs = ls_db_one_docs + ls_db_two_docs

    client.verify_docs_present(url=ls_url, db=ls_db1, expected_docs=ls_db1_db2_docs)
    client.verify_docs_present(url=ls_url, db=ls_db2, expected_docs=ls_db1_db2_docs)
    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_db1_db2_docs)

    client.verify_docs_in_changes(url=sg_admin_url, db=sg_db, expected_docs=ls_db1_db2_docs)
    client.verify_docs_in_changes(url=ls_url, db=ls_db1, expected_docs=ls_db1_db2_docs)
    client.verify_docs_in_changes(url=ls_url, db=ls_db2, expected_docs=ls_db1_db2_docs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_verify_open_revs_with_revs_limit_push_conflict(setup_client_syncgateway_test):
    """Test replication from multiple client dbs to one sync_gateway db

    https://github.com/couchbase/couchbase-lite-ios/issues/1277
    """

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    num_docs = 100
    num_revs = 20

    sg_db = "db"
    sg_user_name = "sg_user"

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(
        cluster_config=cluster_config,
        url=sg_url,
        config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS)
    )

    log_info("Running 'test_verify_open_revs_with_revs_limit_push_conflict'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revs: {}".format(num_revs))

    client = MobileRestClient()

    # Test the endpoint, listener does not support users but should have a default response
    client.get_session(url=ls_url)
    sg_user_channels = ["NBC"]
    client.create_user(url=sg_admin_url, db=sg_db, name=sg_user_name, password="password", channels=sg_user_channels)
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)

    ls_db = client.create_database(url=ls_url, name="ls_db")
    ls_db_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs, id_prefix="ls_db", channels=sg_user_channels)

    # Start replication ls_db -> sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_db_docs)

    client.update_docs(url=sg_url, db=sg_db, docs=ls_db_docs, number_updates=num_revs, auth=sg_session)
    sg_current_doc = client.get_doc(url=sg_url, db=sg_db, doc_id="ls_db_2", auth=sg_session)

    client.update_docs(url=ls_url, db=ls_db, docs=ls_db_docs, number_updates=num_revs)
    ls_current_doc = client.get_doc(url=ls_url, db=ls_db, doc_id="ls_db_2")

    client.wait_for_replication_status_idle(url=ls_url, replication_id=repl_one)

    client.verify_doc_rev_generation(url=ls_url, db=ls_db, doc_id=ls_current_doc["_id"], expected_generation=21)
    client.verify_doc_rev_generation(url=sg_url, db=sg_db, doc_id=sg_current_doc["_id"], expected_generation=21, auth=sg_session)

    expected_ls_revs = [ls_current_doc["_rev"]]
    client.verify_open_revs(url=ls_url, db=ls_db, doc_id=ls_current_doc["_id"], expected_open_revs=expected_ls_revs)

    expected_sg_revs = [ls_current_doc["_rev"], sg_current_doc["_rev"]]
    client.verify_open_revs(url=sg_admin_url, db=sg_db, doc_id=sg_current_doc["_id"], expected_open_revs=expected_sg_revs)
