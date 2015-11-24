import time

import pytest
import concurrent.futures

import lib.settings
from lib.admin import Admin

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_1(cluster):

    abc_doc_num = 100

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["*"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_polling, termination_doc_id="killpolling")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, abc_doc_num, uuid_names=True)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth long poller
                if task_name == "doc_pusher":
                    abc_doc_pusher.add_doc("killpolling")
                elif task_name == "polling":
                    docs_in_changes = future.result()

            except Exception as e:
                print("Futures: error: {}".format(e))

    # 100 channel docs + 1 polling termination doc
    assert len(docs_in_changes.keys()) == abc_doc_num + 1

    # 100 channel docs + 1 polling termination doc
    assert len(abc_doc_pusher.cache) == abc_doc_num + 1

    # Get ids from polling results

    assert set(docs_in_changes) == set(abc_doc_pusher.cache)
