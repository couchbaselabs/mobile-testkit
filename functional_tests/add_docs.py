import pytest
import time
import concurrent.futures

from fixtures import cluster
import lib.settings
from lib.admin import Admin

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

def test_1(cluster):

    cluster.reset("sync_gateway_default_functional_tests.json")
    admin = Admin(cluster.sync_gateways[0])

    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["*"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killcontinuous")] = "poller"
        futures[executor.submit(background_poller, admin, seth)] = "pusher"

        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            if task == "poller":
                try:
                    docs, seq_num = future.result()
                    log.info("DONE POLLING")
                    log.info("DOCS: {}".format(docs))
                    log.info("SEQ_NUM: {}".format(seq_num))
                except Exception as e:
                    # Get docs and last_seq_num if the connection has been closed
                    result = e.args[0]
                    log.info("LAST_SEQ: {}".format(result["last_seq_num"]))

# num_docs = 1000 will result in duplicates in long poll response
num_docs = 1000
def background_poller(admin, user):
    count = 1
    while True:
        user.add_docs(num_docs, bulk=True)
        if count == 10:
            time.sleep(1)
            admin.take_db_offline("db")
        time.sleep(1)
        count += 1