from keywords.utils import log_info
from keywords.utils import log_r
from keywords.MobileRestClient import MobileRestClient
from libraries.data import doc_generators


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

    # Verify docs replicated to client
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=docs)

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=ls_url, db=ls_db, expected_docs=docs)


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

    # Start oneshot pull replication
    repl_id = client.start_replication(
        url=ls_url,
        continuous=continuous,
        from_db=ls_db,
        to_url=sg_one_admin,
        to_db=sg_db
    )

    # Verify docs replicated to client
    client.verify_docs_present(url=sg_one_public, db=sg_db, expected_docs=docs, auth=session)

    # Verify docs show up in client's changes feed
    client.verify_docs_in_changes(url=sg_one_public, db=sg_db, expected_docs=docs, auth=session)