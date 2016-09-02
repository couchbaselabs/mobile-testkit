import json
import re
import time

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from requests.exceptions import HTTPError

from keywords.utils import log_info

from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.SyncGateway import SyncGateway
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient


def initial_pull_replication(ls_url, cluster_config, num_docs, continuous):

    sg_db = "db"
    ls_db = "ls_db"

    sg_one_admin = cluster_config["sync_gateways"][0]["admin"]
    sg_one_public = cluster_config["sync_gateways"][0]["public"]

    log_info(ls_url)
    log_info(sg_one_admin)
    log_info(sg_one_public)

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


def initial_push_replication(ls_url, cluster_config, num_docs, continuous):

    sg_db = "db"
    ls_db = "ls_db"
    seth_channels = ["ABC", "NBC"]

    sg_one_admin = cluster_config["sync_gateways"][0]["admin"]
    sg_one_public = cluster_config["sync_gateways"][0]["public"]

    log_info(ls_url)
    log_info(sg_one_admin)
    log_info(sg_one_public)

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
        assert replications[0]["continuous"] == True, "Running replication should be continuous"
        # Only .NET has an 'error' property
        if "error" in replications[0]:
            assert len(replications[0]["error"]) == 0
    else:
        assert len(replications) == 0, "No replications should be running"


def multiple_replications_not_created_with_same_properties(ls_url, cluster_config):
    sg_db = "db"
    ls_db = "ls_db"

    sg_one_admin = cluster_config["sync_gateways"][0]["admin"]
    sg_one_public = cluster_config["sync_gateways"][0]["public"]

    log_info("Running: multiple_replications_not_created_with_same_properties")
    log_info(ls_url)
    log_info(sg_one_admin)
    log_info(sg_one_public)

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


def multiple_replications_created_with_unique_properties(ls_url, cluster_config):
    sg_db = "db"
    ls_db = "ls_db"

    sg_one_admin = cluster_config["sync_gateways"][0]["admin"]
    sg_one_public = cluster_config["sync_gateways"][0]["public"]

    log_info("Running: multiple_replications_created_with_unique_properties")
    log_info(ls_url)
    log_info(sg_one_admin)
    log_info(sg_one_public)

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
        "filters" : {
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


def replication_with_session_cookie(ls_url, sg_admin_url, sg_url):

    ls_db = "ls_db"
    sg_db = "db"

    log_info("Running 'replication_with_session_cookie' ...")
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



