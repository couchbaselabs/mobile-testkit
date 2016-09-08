import time

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def listener_two_sync_gateways(ls_url, cluster_config, num_docs):

    log_info("ls_url: {}".format(ls_url))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("num_docs: {}".format(num_docs))
    log_info("Running 'listener_two_sync_gateways' ...")

    ls_db_one = "ls_db1"
    ls_db_two = "ls_db2"
    sg_db_one = "sg_db1"
    sg_db_two = "sg_db2"
    sg_one_admin_url = cluster_config["sync_gateways"][0]["admin"]
    sg_two_admin_url = cluster_config["sync_gateways"][1]["admin"]

    client = MobileRestClient()

    # Create dbs on sync_gateway
    client.create_database(sg_one_admin_url, sg_db_one, "walrus:")
    client.create_database(sg_two_admin_url, sg_db_two, "walrus:")

    # Create dbs on LiteServ
    client.create_database(ls_url, ls_db_one)
    client.create_database(ls_url, ls_db_two)

    # Start continuous push pull replication ls_db_one <-> sg_db_one
    repl_one = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )
    repl_two = client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_one
    )

    # Start continuous push pull replication ls_db_two <-> sg_db_two
    repl_three = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )
    repl_four = client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_two
    )

    # Start continuous push pull replication sg_db_one <-> ls_db_two
    repl_five = client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_two
    )
    repl_six = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )

    # Start continuous push pull replication sg_db_two <-> ls_db_one
    repl_seven = client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_one
    )
    repl_eight = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )

    ls_db_one_docs = client.add_docs(url=ls_url, db=ls_db_one, number=num_docs / 2, id_prefix="ls_db_one_doc")
    ls_db_two_docs = client.add_docs(url=ls_url, db=ls_db_two, number=num_docs / 2, id_prefix="ls_db_two_doc")

    all_docs = client.merge(ls_db_one_docs, ls_db_two_docs)

    # Verify docs replicate to each db
    client.verify_docs_present(url=ls_url, db=ls_db_one, expected_docs=all_docs)
    client.verify_docs_present(url=ls_url, db=ls_db_two, expected_docs=all_docs)
    client.verify_docs_present(url=sg_one_admin_url, db=sg_db_one, expected_docs=all_docs)
    client.verify_docs_present(url=sg_two_admin_url, db=sg_db_two, expected_docs=all_docs)

    # Verify changes feeds for each db
    client.verify_docs_in_changes(url=ls_url, db=ls_db_one, expected_docs=all_docs)
    client.verify_docs_in_changes(url=ls_url, db=ls_db_two, expected_docs=all_docs)
    client.verify_docs_in_changes(url=sg_one_admin_url, db=sg_db_one, expected_docs=all_docs)
    client.verify_docs_in_changes(url=sg_two_admin_url, db=sg_db_two, expected_docs=all_docs)
