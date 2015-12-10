import time

import pytest
import concurrent.futures

import lib.settings
from lib.admin import Admin
from lib.verify import verify_changes
from lib.verify import verify_same_docs

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_continuous_changes_sanity(cluster):

    abc_doc_num = 5000

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["*"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_continuous, termination_doc_id="killcontinuous")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, abc_doc_num)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth long poller
                if task_name == "doc_pusher":
                    abc_doc_pusher.add_doc("killcontinuous")
                elif task_name == "polling":
                    docs_in_changes = future.result()

            except Exception as e:
                print("Futures: error: {}".format(e))

    # Expect number of docs + the termination doc
    verify_changes(abc_doc_pusher, expected_num_docs=abc_doc_num + 1, expected_num_revisions=0, expected_docs=abc_doc_pusher.cache)

    # Expect number of docs + the termination doc + _user doc
    verify_same_docs(expected_num_docs=abc_doc_num + 1, doc_dict_one=docs_in_changes, doc_dict_two=abc_doc_pusher.cache)
