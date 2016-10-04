import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.usefixtures("setup_client_2sgs_suite")
def listener_two_sync_gateways(ls_url, cluster_config, num_docs):
    """
    Port of https://github.com/couchbaselabs/sync-gateway-tests/blob/master/tests/cbl-replication-mismatch-2-gateways.js
    Scenario:
      1. Start 2 sync_gateways
      2. Create sg_db_one db on sync_gateway one
      3. Create sg_db_two db on sync_gateway two
      4. Create ls_db_one and ls_db_two on Liteserv
      5. Setup continuous push / pull replication from ls_db_one <-> sg_db_one
      6. Setup continuous push / pull replication from ls_db_two <-> sg_db_two
      7. Setup continuous push / pull replication from sg_db_one <-> ls_db_two
      8. Setup continuous push / pull replication from sg_db_two <-> ls_db_one
      9. Add num_docs / 2 to each liteserv database
      10. Verify each database has num_docs docs
      11. Verify all_docs in all dbs
      12. Verify changes feed for sg_db_one and sg_db_two
      13. Verify chnages feed for ls_db_one and ls_db_two
    """

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
