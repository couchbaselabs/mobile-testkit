import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from testkit.cluster import Cluster

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.CouchbaseServer import CouchbaseServer


def test_distributed_index_rebalance_sanity(cluster_config):
    log_info(cluster_config)

    admin_sg_one = cluster_config["sync_gateways"][0]["admin"]
    sg_one_url = cluster_config["sync_gateways"][0]["public"]
    cbs_one_url = cluster_config["couchbase_servers"][0]
    cbs_two_url = cluster_config["couchbase_servers"][1]

    sg_db = "db"
    num_docs = 100
    num_updates = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    server = CouchbaseServer()

    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    with ThreadPoolExecutor(5) as executor:

        # Add docs to sg
        log_info("Adding docs to sync_gateway")
        add_docs_task = executor.submit(client.add_docs, sg_one_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        docs = add_docs_task.result()

        # Start updating docs and rebalance out one CBS node
        log_info("Updating docs on sync_gateway")
        update_docs_task = executor.submit(client.update_docs, sg_one_url, sg_db, docs, num_updates, auth=session)

        rebalance_task = executor.submit(server.rebalance_out, admin_server=cbs_one_url, server_to_remove=cbs_two_url)
        assert rebalance_task.result(), "Rebalance out unsuccessful for {}!".format(cbs_two_url)

        updated_docs = update_docs_task.result()
        log_info(updated_docs)

    # Verify docs / revisions present
    client.verify_docs_present(sg_one_url, sg_db, updated_docs, auth=session)

    # Verify docs revisions in changes feed
    client.verify_docs_in_changes(sg_one_url, sg_db, updated_docs, auth=session)

    # Rebalance Server back in to the pool
    assert server.rebalance_in(admin_server=cbs_one_url, server_to_add=cbs_two_url), "Could not rebalance node back in .."

    # Verify all sgs and accels are still running
    cluster = Cluster()
    errors = cluster.verify_alive("distributed_index")
    assert (len(errors) == 0)