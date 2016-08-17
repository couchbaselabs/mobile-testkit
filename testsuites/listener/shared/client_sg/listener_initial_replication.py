from keywords.utils import log_info
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