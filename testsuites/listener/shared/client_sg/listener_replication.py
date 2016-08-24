import json

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.SyncGateway import SyncGateway
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient


def large_initial_pull_replication(ls_url, cluster_config, num_docs, continuous):

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

    # Create 10000 docs on sync_gateway
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

    if continuous:
        log_info("Waiting for replication status 'Idle' for: {}".format(repl_id))
        client.wait_for_replication_status_idle(ls_url, repl_id)
    else:
        log_info("Waiting for no replications".format(repl_id))
        client.wait_for_no_replications(ls_url)

    # Verify docs replicated to client
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs)

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=ls_url, db=ls_db, expected_docs=docs)

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


def large_initial_push_replication(ls_url, cluster_config, num_docs, continuous):

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

    # Create 10000 docs on LiteServ
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

    repl_id = "repl001"

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
            response_id = future.result()
            assert response_id == repl_id, "Expected replication id: {} Actual: {}".format(
                repl_id,
                response_id
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
    replications = client.get_replications(ls_url)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual {}".format(
        0,
        len(replications)
    )

    # Global var gets incremented according to Pasin.
    repl_id = "repl052"

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
            response_id = future.result()
            assert response_id == repl_id, "Expected replication id: {} Actual: {}".format(
                repl_id,
                response_id
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
    assert repl_one == "repl001", "Replication {} should have id: repl001".format(repl_one)

    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db,
        doc_ids=["doc_1", "doc_2"]
    )
    assert repl_two == "repl002", "Replication {} should have id: repl002".format(repl_two)

    # Create doc filter and add to the design doc
    filters = {
        "language": "javascript",
        "filters" : {
            "sample_filter" : "function(doc, req) { if (doc.type && doc.type === \"skip\") { return false; } return true; }"
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
    assert repl_three == "repl003", "Replication {} should have id: repl003".format(repl_three)

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
    repl_seven = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db
    )
    assert repl_seven == "repl007", "Replication {} should have id: repl007".format(repl_seven)

    # Start filtered pull from sync gateway to LiteServ
    repl_eight = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db,
        channels_filter=["ABC", "CBS"]
    )
    assert repl_eight == "repl008", "Replication {} should have id: repl008".format(repl_eight)

    # Verify 3 replicaitons are running
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 2, "Number of replications, Expected: {} Actual: {}".format(
        2,
        len(replications)
    )

    # Stop repl007
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db
    )

    # Stop repl008
    client.stop_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_one_admin,
        from_db=sg_db,
        to_db=ls_db,
        channels_filter=["ABC", "CBS"]
    )

    # Verify no replications are running
    replications = client.get_replications(ls_url)
    log_info(replications)
    assert len(replications) == 0, "Number of replications, Expected: {} Actual: {}".format(
        0,
        len(replications)
    )


def replication_with_session_cookie(ls_url, sg_admin_url, sg_url):
    log_info("Running 'replication_with_session_cookie' ...")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    sg = SyncGateway()
    sg.stop_sync_gateway(sg_url)
    sg.start_sync_gateway(sg_url, "{}/walrus-user.json".format(SYNC_GATEWAY_CONFIGS))



