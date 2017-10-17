import json
import re
import time
import pytest

from keywords import document
from keywords import attachment
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from libraries.testkit import cluster


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
        channels=["ABC"],
        auth=session
    )
    assert len(docs) == num_docs

    # Add a poll to make sure all of the docs have propagated to sync_gateway's _changes before initiating
    # the one shot pull replication to ensure that the client is aware of all of the docs to pull
    client.verify_docs_in_changes(url=sg_one_public, db=sg_db, expected_docs=docs, auth=session, polling_interval=10)

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
        log_info("Waiting for no replications: {}".format(repl_id))
        client.wait_for_no_replications(ls_url)

    # Verify docs replicated to client
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs, timeout=240)

    all_docs_replicated_time = time.time() - start
    log_info("Replication took: {}s".format(all_docs_replicated_time))

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=ls_url, db=ls_db, expected_docs=docs)

    if continuous:
        count = 0
        max_retries = 3
        # Try in a loop to handle a delay between getting the changes and replication status turning to idle
        while True:

            replications = client.get_replications(url=ls_url)

            assert len(replications) == 1, "There should only be one replication running"
            assert replications[0]["continuous"], "Running replication should be continuous"

            try:
                assert replications[0]["status"] == "Idle", "Replication Status should be 'Idle'"
                break
            except AssertionError:
                log_info("All changes have come through but replication status is not idle yet!")
                count += 1

                # Fail if count hits max retries
                assert count != max_retries

                time.sleep(1)

        # Only .NET has an 'error' property
        if "error" in replications[0]:
            assert len(replications[0]["error"]) == 0

    else:
        replications = client.get_replications(url=ls_url)
        assert len(replications) == 0, "No replications should be running"


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
@pytest.mark.parametrize("num_docs, need_attachments, replication_after_backgroundApp", [
    (1000, True, False),
    (10000, False, False),
    (10000, False, False),
    (100000, False, False),
    (100000, False, False),
    (100000, False, True)
])
def test_initial_pull_replication_background_apprun(setup_client_syncgateway_test, num_docs, need_attachments, replication_after_backgroundApp):
    """
    1. Prepare sync-gateway to have 10000 documents.
    2. Create a single shot / continuous pull replicator and to pull the docs into a database.
    3. Verify if all of the docs get pulled.
    Referenced issue: couchbase/couchbase-lite-android#955.
    """

    sg_db = "db"
    ls_db = "ls_db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]
    liteserv = setup_client_syncgateway_test["liteserv"]
    liteserv_platform = setup_client_syncgateway_test["liteserv_platform"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    
    if liteserv_platform != "ios":
        pytest.skip('This test only valid for mobile')
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_user(sg_one_admin, sg_db, "seth", password="password", channels=["ABC", "NBC"])
    session = client.create_session(sg_one_admin, sg_db, "seth")

    # Add 'number_of_sg_docs' to Sync Gateway
    bulk_docs_resp = []
    if need_attachments:
        sg_doc_bodies = document.create_docs(
            doc_id_prefix="seeded_doc",
            number=num_docs,
            attachments_generator=attachment.generate_2_png_100_100,
            channels=["ABC"]
        )
    else:
        sg_doc_bodies = document.create_docs(doc_id_prefix='seeded_doc', number=num_docs, channels=["ABC"])
    # if adding bulk docs with huge attachment more than 5000 fails
    for x in xrange(0, len(sg_doc_bodies), 100000):
        chunk_docs = sg_doc_bodies[x:x + 100000]
        ch_bulk_docs_resp = client.add_bulk_docs(url=sg_one_public, db=sg_db, docs=chunk_docs, auth=session)
        log_info("length of bulk docs resp{}".format(len(ch_bulk_docs_resp)))
        bulk_docs_resp += ch_bulk_docs_resp
    # docs = client.add_bulk_docs(url=sg_one_public, db=sg_db, docs=sg_doc_bodies, auth=session)
    assert len(bulk_docs_resp) == num_docs

    # Add a poll to make sure all of the docs have propagated to sync_gateway's _changes before initiating
    # the one shot pull replication to ensure that the client is aware of all of the docs to pull
    client.verify_docs_in_changes(url=sg_one_public, db=sg_db, expected_docs=bulk_docs_resp, auth=session, polling_interval=10)

    # Start oneshot pull replication with app background
    client.create_database(url=ls_url, name=ls_db)
    if replication_after_backgroundApp:
        liteserv.close_app()
        time.sleep(2)
        client.start_replication(
            url=ls_url,
            continuous=True,
            from_url=sg_one_admin,
            from_db=sg_db,
            to_db=ls_db
        )
    else:
        client.start_replication(
            url=ls_url,
            continuous=True,
            from_url=sg_one_admin,
            from_db=sg_db,
            to_db=ls_db
        )
        time.sleep(5)
        liteserv.close_app()

    # Verify docs replicated to client
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=bulk_docs_resp, timeout=3600)

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=ls_url, db=ls_db, expected_docs=bulk_docs_resp)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
    assert len(docs) == num_docs

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
        log_info("Waiting for no replications: {}".format(repl_id))
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
@pytest.mark.session
@pytest.mark.parametrize("num_docs, need_attachments, replication_after_backgroundApp", [
    (1000, True, False),
    (10000, False, False),
    (10000, False, False)
])
def test_push_replication_with_backgroundApp(setup_client_syncgateway_test, num_docs, need_attachments, replication_after_backgroundApp):
    """
    1. Prepare LiteServ to have 10000 documents.
    2. Create a single shot push / continuous replicator and to push the docs into a sync_gateway database.
    3. Verify if all of the docs get pushed.
    """

    sg_db = "db"
    ls_db = "ls_db"
    seth_channels = ["ABC", "NBC"]

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]
    liteserv = setup_client_syncgateway_test["liteserv"]
    liteserv_platform = setup_client_syncgateway_test["liteserv_platform"]
    
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    if liteserv_platform != "ios":
        pytest.skip('This test only valid for mobile')
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin: {}".format(sg_one_admin))
    log_info("sg_one_public: {}".format(sg_one_public))

    client = MobileRestClient()
    client.create_user(sg_one_admin, sg_db, "seth", password="password", channels=seth_channels)
    session = client.create_session(sg_one_admin, sg_db, "seth")

    client.create_database(url=ls_url, name=ls_db)
    bulk_docs_resp = []
    if need_attachments:
        doc_bodies = document.create_docs(
            doc_id_prefix="seeded_doc",
            number=num_docs,
            attachments_generator=attachment.generate_2_png_100_100,
            channels=seth_channels
        )
    else:
        doc_bodies = document.create_docs(doc_id_prefix='seeded_doc', number=num_docs, channels=seth_channels)

    for x in xrange(0, len(doc_bodies), 100000):
        chunk_docs = doc_bodies[x:x + 100000]
        ch_bulk_docs_resp = client.add_bulk_docs(url=ls_url, db=ls_db, docs=chunk_docs, auth=session)
        log_info("length of bulk docs resp{}".format(len(ch_bulk_docs_resp)))
        bulk_docs_resp += ch_bulk_docs_resp
    assert len(bulk_docs_resp) == num_docs

    # Start push replication with app background
    if replication_after_backgroundApp:
        liteserv.close_app()
        time.sleep(2)
        client.start_replication(
            url=ls_url,
            continuous=True,
            from_db=ls_db,
            to_url=sg_one_admin,
            to_db=sg_db
        )
    else:
        client.start_replication(
            url=ls_url,
            continuous=True,
            from_db=ls_db,
            to_url=sg_one_admin,
            to_db=sg_db
        )
        time.sleep(3)
        liteserv.close_app()

    # Verify docs replicated to sync_gateway
    client.verify_docs_present(url=sg_one_public, db=sg_db, expected_docs=bulk_docs_resp, auth=session, timeout=3600)

    # Verify docs show up in sync_gateway's changes feed
    client.verify_docs_in_changes(url=sg_one_public, db=sg_db, expected_docs=bulk_docs_resp, auth=session)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_one_admin = setup_client_syncgateway_test["sg_admin_url"]
    sg_one_public = setup_client_syncgateway_test["sg_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
@pytest.mark.session
def test_replication_with_session_cookie(setup_client_syncgateway_test):
    """Regression test for https://github.com/couchbase/couchbase-lite-android/issues/817
    1. SyncGateway Config with One user added (e.g. user1 / 1234)
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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_user", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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

    num_docs_pushed = 100

    # Sanity test docs
    ls_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs_pushed, id_prefix="ls_doc", channels=["ABC"])
    assert len(ls_docs) == num_docs_pushed

    sg_docs = client.add_docs(url=sg_url, db=sg_db, number=num_docs_pushed, id_prefix="sg_doc", auth=session, channels=["ABC"])
    assert len(sg_docs) == num_docs_pushed

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
@pytest.mark.session
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
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_revslimit", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
    assert len(ls_db_docs) == num_docs

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
    assert len(ls_db_docs) == 10

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
def test_replication_with_multiple_client_dbs_and_single_sync_gateway_db(setup_client_syncgateway_test):
    """Test replication from multiple client dbs to one sync_gateway db"""

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    num_docs = 1000

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("Running 'test_replication_with_multiple_client_dbs_and_single_sync_gateway_db'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()

    sg_db = "db"
    ls_db1 = client.create_database(url=ls_url, name="ls_db1")
    ls_db2 = client.create_database(url=ls_url, name="ls_db2")

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
    assert len(ls_db_one_docs) == 1000

    ls_db_two_docs = client.add_docs(url=ls_url, db=ls_db2, number=num_docs, id_prefix=ls_db2)
    assert len(ls_db_two_docs) == 1000

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
@pytest.mark.session
def test_verify_open_revs_with_revs_limit_push_conflict(setup_client_syncgateway_test):
    """Test replication from multiple client dbs to one sync_gateway db

    https://github.com/couchbase/couchbase-lite-ios/issues/1277
    """

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    num_docs = 100
    num_revs = 20

    sg_db = "db"
    sg_user_name = "sg_user"

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

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
    assert len(ls_db_docs) == num_docs

    # Start replication ls_db -> sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_db_docs)

    # Update docs on sync gateway
    client.update_docs(url=sg_url, db=sg_db, docs=ls_db_docs, number_updates=num_revs, auth=sg_session)
    sg_current_doc = client.get_doc(url=sg_url, db=sg_db, doc_id="ls_db_2", auth=sg_session)

    # Update docs on client
    client.update_docs(url=ls_url, db=ls_db, docs=ls_db_docs, number_updates=num_revs)
    ls_current_doc = client.get_doc(url=ls_url, db=ls_db, doc_id="ls_db_2")

    client.wait_for_replication_status_idle(url=ls_url, replication_id=repl_one)

    client.verify_doc_rev_generation(url=ls_url, db=ls_db, doc_id=ls_current_doc["_id"], expected_generation=21)
    client.verify_doc_rev_generation(url=sg_url, db=sg_db, doc_id=sg_current_doc["_id"], expected_generation=21, auth=sg_session)

    expected_ls_revs = [ls_current_doc["_rev"]]
    client.verify_open_revs(url=ls_url, db=ls_db, doc_id=ls_current_doc["_id"], expected_open_revs=expected_ls_revs)

    expected_sg_revs = [ls_current_doc["_rev"], sg_current_doc["_rev"]]
    client.verify_open_revs(url=sg_admin_url, db=sg_db, doc_id=sg_current_doc["_id"], expected_open_revs=expected_sg_revs)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
@pytest.mark.session
def test_replication_with_session_cookie_short_ttl(setup_client_syncgateway_test):
    """Regression test for https://github.com/couchbaselabs/mobile-testkit/issues/1110
    1. SyncGateway Config with One user added (e.g. user1 / 1234)
    2. Create a new session on SGW for the user1 by using POST /_session.
       Capture the SyncGatewaySession cookie from the set-cookie in the response header.
    3. Start continuous push replicator on the LiteServ with SyncGatewaySession cookie.
       Make sure that the replicators start correctly
       Let the replicator run for more than 10% of the session expiry time specified when the session was created in step 2
    4. Cancel both push and pull replicator on the LiteServ
    5. Delete the session from SGW by sending DELETE /_sessions/ to SGW
    6. Repeat steps 2 through 6
    """

    ls_db = "ls_db"
    sg_db = "db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_user", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("Running 'test_replication_with_session_cookie_short_ttl'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)

    # Get session header for user_1
    cookie_name, session_id = client.create_session(url=sg_admin_url, db=sg_db, name="user_1", password="foo", ttl=10)

    # session_header: SyncGatewaySession=a483be3248f740d810c09eb2c1b1f9198141bb15; Path=/db; Expires=Fri, 14 Apr 2017 03:54:46 GMT
    session_header = "{}={}".format(cookie_name, session_id)
    assert session_header.startswith("SyncGatewaySession")

    log_info("session_header: {}".format(session_header))

    # Start authenticated push replication
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_url,
        to_db=sg_db,
        to_auth=session_header
    )

    # Wait for 1 replications to be 'Idle', On .NET they may not be immediately available via _active_tasks
    client.wait_for_replication_status_idle(ls_url, repl_one)

    replications = client.get_replications(ls_url)
    assert len(replications) == 1, "1 replications (push should be running)"

    num_docs_pushed = 1
    attempts = 3

    # Add 3 docs and sleep in between
    while attempts > 0:
        # Sanity test docs
        ls_prefix = "ls_doc1_" + str(attempts)
        ls_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs_pushed, id_prefix=ls_prefix, channels=["ABC"])
        assert len(ls_docs) == num_docs_pushed

        attempts -= 1
        # Sleep for 5 seconds after every add so as to expire the ttl
        time.sleep(5)

    log_info(ls_docs)

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_docs)
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=ls_docs)

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

    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "All replications should be stopped"

    # Delete the session
    client.delete_session(url=sg_admin_url, db=sg_db, user_name="user_1", session_id=session_id)

    # Get session header for user_1
    cookie_name, session_id = client.create_session(url=sg_admin_url, db=sg_db, name="user_1", password="foo", ttl=10)

    # session_header: SyncGatewaySession=a483be3248f740d810c09eb2c1b1f9198141bb15; Path=/db; Expires=Fri, 14 Apr 2017 03:54:46 GMT
    session_header = "{}={}".format(cookie_name, session_id)
    assert session_header.startswith("SyncGatewaySession")

    log_info("session_header: {}".format(session_header))

    # Start authenticated push replication
    # The bug was that the CBL replication here will use the previous
    # session's cookie and get a 401 error
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_url,
        to_db=sg_db,
        to_auth=session_header
    )

    # Wait for 1 replications to be 'Idle', On .NET they may not be immediately available via _active_tasks
    client.wait_for_replication_status_idle(ls_url, repl_one)

    replications = client.get_replications(ls_url)
    assert len(replications) == 1, "1 replications (push should be running)"

    num_docs_pushed = 1
    attempts = 3

    # Add 3 docs and sleep in between
    while attempts > 0:
        # Sanity test docs
        ls_prefix = "ls_doc2_" + str(attempts)
        ls_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs_pushed, id_prefix=ls_prefix, channels=["ABC"])
        assert len(ls_docs) == num_docs_pushed

        attempts -= 1
        # Sleep for 5 seconds after every add so as to expire the ttl
        time.sleep(5)

    log_info(ls_docs)

    client.verify_docs_present(url=sg_admin_url, db=sg_db, expected_docs=ls_docs)
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=ls_docs)

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

    client.wait_for_no_replications(ls_url)
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "All replications should be stopped"

    # Delete the session
    client.delete_session(url=sg_admin_url, db=sg_db, user_name="user_1", session_id=session_id)


@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
def test_replication_attachments_survive_channel_removal(setup_client_syncgateway_test):
    """Regression test for https://github.com/couchbase/couchbase-lite-net/issues/910
    1. SyncGateway Config with One user added (e.g. user1 / 1234) who has access to a limited
       set of channels (e.g. ["user_channel"]) and GUEST disabled
    2. Start authenticated continuous pull replication
    3. Add a document that gets assigned to the user's channel, and verify that it is pulled
    4. Stop the pull replication started in (2)
    5. Add a few arbitrary edits to the document created in (3), including adding at least
       one attachment
    6. Add an edit to the document created in (3) that removes it from the user's channel
    7. Repeat step (2)
    8. Add an edit to the document created in (3) that keep the attachments intact, as well
       as adds the document back into the user's channel
    9. Verify that the document and attachment are both present in the local DB
    """

    # Here is the general idea, tweak and remove this comment
    ls_db = "ls_db"
    sg_db = "db"

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    # Create the config mentioned in step 1
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests_user", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("Running 'test_replication_attachments_survive_channel_removal'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)
    abc_channels = ["ABC"]
    nbc_channels = ["NBC"]
    num_of_docs = 10
    client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=abc_channels)
    session = client.create_session(sg_admin_url, sg_db, "autotest")
    client.create_user(sg_admin_url, sg_db, "autotest2", password="password", channels=nbc_channels)
    session1 = client.create_session(sg_admin_url, sg_db, "autotest2")

    pull = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url,
        from_db=sg_db,
        from_auth=session,
        to_db=ls_db,
    )

    docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=num_of_docs,
        id_prefix="seeded_doc",
        generator="four_k",
        channels=abc_channels,
        auth=session
    )

    client.wait_for_replication_status_idle(ls_url, pull)
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs, timeout=240)
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_db=sg_db,
        from_url=sg_url,
        to_db=ls_db
    )

    # steps 5 and 6
    for doc in docs:
        log_info("doc is is {}".format(doc))
        client.update_doc(url=sg_url, db=sg_db, doc_id=doc["id"], number_updates=1, attachment_name="sample_text.txt", delay=0.1, auth=session, channels=abc_channels)
    client.update_docs(url=sg_url, db=sg_db, docs=docs, number_updates=1, delay=0.1, auth=session, channels=nbc_channels)
    # Continue with step 7
    pull = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url,
        from_db=sg_db,
        from_auth=session,
        to_db=ls_db,
    )
    client.wait_for_replication_status_idle(ls_url, pull)

    # Step 8
    updated_docs = client.update_docs(url=sg_url, db=sg_db, docs=docs, number_updates=1, delay=0.1, auth=session1, channels=abc_channels)
    # Step 9
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=updated_docs, timeout=240)
    for doc in updated_docs:
        att = client.get_attachment(
            url=ls_url,
            db=ls_db,
            doc_id=doc["id"],
            attachment_name="sample_text.txt"
        )
        expected_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\nDuis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.\nExcepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
        assert expected_text == att
