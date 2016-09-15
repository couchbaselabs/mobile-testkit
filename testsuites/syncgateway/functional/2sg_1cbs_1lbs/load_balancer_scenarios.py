import time
import concurrent.futures

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def test_load_balance_sanity(cluster_config):
    log_info(cluster_config)

    admin_sg_one = cluster_config["sync_gateways"][0]["admin"]
    sg_one_url = cluster_config["sync_gateways"][0]["public"]
    lb_url = cluster_config["load_balancers"][0]

    sg_db = "db"
    num_docs = 1000
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()

    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    log_info(user)
    log_info(session)

    log_info("Adding docs to the load balancer ...")

    ct = ChangesTracker(url=lb_url, db=sg_db, auth=session)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        log_info("Starting ...")
        executor.submit(ct.start)
        log_info("Adding docs ...")
        add_docs_task = executor.submit(client.add_docs, lb_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)

        docs = add_docs_task.result()

        log_info("Adding docs done")
        wait_for_changes = executor.submit(ct.wait_until, docs)

        if wait_for_changes.result():
            log_info("Stopping ...")
            log_info("Found all docs ...")
            executor.submit(ct.stop)
        else:
            executor.submit(ct.stop)
            raise Exception("Could not find all changes in feed before timeout!!")
