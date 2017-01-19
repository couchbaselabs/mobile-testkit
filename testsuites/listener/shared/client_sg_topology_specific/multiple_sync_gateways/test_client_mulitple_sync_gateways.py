import pytest

from keywords.utils import log_info
from keywords.SyncGateway import SyncGateway
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.MobileRestClient import MobileRestClient
from libraries.testkit import cluster
from keywords.CouchbaseServer import CouchbaseServer


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
def test_listener_two_sync_gateways(setup_client_syncgateway_test):
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

    num_docs = 500

    ls_url = setup_client_syncgateway_test["ls_url"]
    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]

    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_config)

    sg_one_admin_url = topology["sync_gateways"][0]["admin"]
    sg_two_admin_url = topology["sync_gateways"][1]["admin"]
    cb_server_url = topology["couchbase_servers"][0]

    log_info("Sync Gateway 1 admin url: {}".format(sg_one_admin_url))
    log_info("Sync Gateway 2 admin url: {}".format(sg_two_admin_url))
    log_info("Couchbase Server url: {}".format(cb_server_url))

    c = cluster.Cluster(cluster_config)
    sg_config_path = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c.reset(sg_config_path=sg_config_path)

    ls_db_one = "ls_db1"
    ls_db_two = "ls_db2"
    sg_db_one = "sg_db1"
    sg_db_two = "sg_db2"

    log_info("ls_url: {}".format(ls_url))
    log_info("sg_one_admin_url: {}".format(sg_one_admin_url))
    log_info("sg_two_admin_url: {}".format(sg_two_admin_url))
    log_info("num_docs: {}".format(num_docs))
    log_info("Running 'test_listener_two_sync_gateways' ...")

    client = MobileRestClient()

    # Delete dbs on sync_gateways
    client.delete_databases(url=sg_one_admin_url)
    client.delete_databases(url=sg_two_admin_url)

    if sg_mode == "di":
        accel_url = topology["sg_accels"][0]
        client.delete_databases(url=accel_url)

    # Create backing stores for each db
    cb_server = CouchbaseServer(cb_server_url)
    cb_server.delete_buckets()

    cb_server.create_buckets(["data-bucket-1", "data-bucket-2", "index-bucket-1", "index-bucket-2"])

    if sg_mode == "di":

        # Create dbs on sync_gateway
        client.create_database(
            url=sg_one_admin_url,
            sync_gateway_mode=sg_mode,
            name=sg_db_one,
            server_url=cb_server_url,
            bucket_name="data-bucket-1",
            index_bucket_name="index-bucket-1",
            is_index_writer=False
        )
        client.create_database(
            url=sg_two_admin_url,
            name=sg_db_two,
            sync_gateway_mode=sg_mode,
            server_url=cb_server_url,
            bucket_name="data-bucket-2",
            index_bucket_name="index-bucket-2",
            is_index_writer=False
        )

        # Create dbs on sg_accel
        client.create_database(
            url=accel_url,
            sync_gateway_mode=sg_mode,
            name=sg_db_one,
            server_url=cb_server_url,
            bucket_name="data-bucket-1",
            index_bucket_name="index-bucket-1",
            is_index_writer=True
        )
        client.create_database(
            url=accel_url,
            name=sg_db_two,
            sync_gateway_mode=sg_mode,
            server_url=cb_server_url,
            bucket_name="data-bucket-2",
            index_bucket_name="index-bucket-2",
            is_index_writer=True
        )

    else:

        # Create dbs on sync_gateway
        client.create_database(
            url=sg_one_admin_url,
            sync_gateway_mode=sg_mode,
            name=sg_db_one,
            server_url=cb_server_url,
            bucket_name="data-bucket-1"
        )
        client.create_database(
            url=sg_two_admin_url,
            name=sg_db_two,
            sync_gateway_mode=sg_mode,
            server_url=cb_server_url,
            bucket_name="data-bucket-2",
        )

    import pdb
    pdb.set_trace()

    # Create dbs on LiteServ
    client.create_database(ls_url, ls_db_one)
    client.create_database(ls_url, ls_db_two)

    # Start continuous push pull replication ls_db_one <-> sg_db_one
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_one
    )

    # Start continuous push pull replication ls_db_two <-> sg_db_two
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_two
    )

    # Start continuous push pull replication sg_db_one <-> ls_db_two
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_one_admin_url, from_db=sg_db_one,
        to_db=ls_db_two
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_two,
        to_url=sg_one_admin_url, to_db=sg_db_one
    )

    # Start continuous push pull replication sg_db_two <-> ls_db_one
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_two_admin_url, from_db=sg_db_two,
        to_db=ls_db_one
    )
    client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db_one,
        to_url=sg_two_admin_url, to_db=sg_db_two
    )

    ls_db_one_docs = client.add_docs(url=ls_url, db=ls_db_one, number=num_docs / 2, id_prefix="ls_db_one_doc")
    assert len(ls_db_one_docs) == num_docs / 2

    ls_db_two_docs = client.add_docs(url=ls_url, db=ls_db_two, number=num_docs / 2, id_prefix="ls_db_two_doc")
    assert len(ls_db_two_docs) == num_docs / 2

    all_docs = client.merge(ls_db_one_docs, ls_db_two_docs)
    assert len(all_docs) == 500

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
