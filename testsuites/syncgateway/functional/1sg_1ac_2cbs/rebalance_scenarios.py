import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.CouchbaseServer import CouchbaseServer
from keywords.ChangesTracker import ChangesTracker


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

    # ct = ChangesTracker(url=sg_one_url, db=sg_db, auth=session)

    with ThreadPoolExecutor(5) as executor:

        # Start changes tracker
        # executor.submit(ct.start)

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

        # Make sure all the changes for the doc updates show up in the changes tracker
        # wait_for_changes_task = executor.submit(ct.wait_until, updated_docs)

        # if wait_for_changes_task.result():
        #     log_info("Stopping ...")
        #     log_info("Found all docs ...")
        #     executor.submit(ct.stop)
        # else:
        #    executor.submit(ct.stop)
        #    raise Exception("Could not find all changes in feed before timeout!!")

    # Rebalance Server back in to the pool
    server.rebalance_in(admin_server=cbs_one_url, server_to_add=cbs_two_url)

