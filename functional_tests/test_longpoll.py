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
@pytest.mark.parametrize(
        "conf,num_docs,num_revisions", [
            ("sync_gateway_default_functional_tests.json", 5000, 1),
            ("sync_gateway_default_functional_tests.json", 5000, 10)
        ],
        ids=["DI-1", "DI-2"]
)
def test_longpoll_changes_parametrized(cluster,conf, num_docs, num_revisions):

    cluster.reset(config=conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killpolling")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, num_docs)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth long poller
                if task_name == "doc_pusher":
                    abc_doc_pusher.update_docs(num_revs_per_doc=num_revisions)

                    time.sleep(5)

                    doc_terminator.add_doc("killpolling")
                elif task_name == "polling":
                    docs_in_changes = future.result()

            except Exception as e:
                print("Futures: error: {}".format(e))

    # Verify abc_docs_pusher gets the correct docs in changes feed
    verify_changes(abc_doc_pusher, expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=abc_doc_pusher.cache)

    # Verify docs from seth continous changes is the same as abc_docs_pusher's docs
    verify_same_docs(expected_num_docs=num_docs, doc_dict_one=docs_in_changes, doc_dict_two=abc_doc_pusher.cache)


@pytest.mark.distributed_index
@pytest.mark.sanity
@pytest.mark.parametrize("num_docs", [10])
@pytest.mark.parametrize("num_revisions", [10])
def test_longpoll_changes_sanity(cluster, num_docs, num_revisions):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killpolling")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, num_docs)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            try:
                task_name = futures[future]

                # Send termination doc to seth long poller
                if task_name == "doc_pusher":
                    abc_doc_pusher.update_docs(num_revs_per_doc=num_revisions)
                    doc_terminator.add_doc("killpolling")
                elif task_name == "polling":
                    docs_in_changes = future.result()

            except Exception as e:
                print("Futures: error: {}".format(e))

    # Verify abc_docs_pusher gets the correct docs in changes feed
    verify_changes(abc_doc_pusher, expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=abc_doc_pusher.cache)

    # Verify docs from seth continous changes is the same as abc_docs_pusher's docs
    verify_same_docs(expected_num_docs=num_docs, doc_dict_one=docs_in_changes, doc_dict_two=abc_doc_pusher.cache)
