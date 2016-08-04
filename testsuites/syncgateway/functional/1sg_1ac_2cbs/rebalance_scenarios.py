import time
import concurrent.futures

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def test_distributed_index_rebalance_sanity(cluster_config):
    log_info(cluster_config)

    admin_sg_one = cluster_config["sync_gateways"][0]["admin"]
    sg_one_url = cluster_config["sync_gateways"][0]["public"]

    sg_db = "db"
    num_docs = 100
    num_updates = 100
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()

    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        # Add docs to sg
        log_info("Adding docs to sync_gateway")
        add_docs_task = executor.submit(client.add_docs, sg_one_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        docs = add_docs_task.result()

        # Start updating docs and rebalance out one CBS node
        log_info("Updating docs on sync_gateway")
        update_docs_task = executor.submit(client.update_docs, sg_one_url, sg_db, docs, num_updates, auth=session)

        updated_docs = update_docs_task.result()
        log_info(updated_docs)

    # log_info(user)
    # log_info(session)
    #
    # log_info("Adding docs to the load balancer ...")
    #
    # ct = ChangesTracker(url=sg_one_url, db=sg_db, auth=session)
    #
    # with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    #     log_info("Starting ...")
    #     executor.submit(ct.start)
    #     log_info("Adding docs ...")
    #     add_docs_task = executor.submit(client.add_docs, sg_one_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
    #
    #     docs = add_docs_task.result()
    #
    #     log_info("Adding docs done")
    #     wait_for_changes = executor.submit(ct.wait_until, docs)
    #
    #     if wait_for_changes.result():
    #         log_info("Stopping ...")
    #         log_info("Found all docs ...")
    #         executor.submit(ct.stop)
    #     else:
    #        executor.submit(ct.stop)
    #        raise Exception("Could not find all changes in feed before timeout!!")
