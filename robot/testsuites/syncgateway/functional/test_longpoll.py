import time

import pytest
import concurrent.futures

import testkit.settings
from testkit.admin import Admin
from testkit.cluster import Cluster
from testkit.verify import verify_changes
from testkit.verify import verify_same_docs

import testkit.settings
import logging
log = logging.getLogger(testkit.settings.LOGGER)


def test_longpoll_changes_parametrized(conf, num_docs, num_revisions):

    log.info("conf: {}".format(conf))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=testkit.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killpolling")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, num_docs)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            task_name = futures[future]

            # Send termination doc to seth long poller
            if task_name == "doc_pusher":
                abc_doc_pusher.update_docs(num_revs_per_doc=num_revisions)

                time.sleep(5)

                doc_terminator.add_doc("killpolling")
            elif task_name == "polling":
                docs_in_changes, last_seq = future.result()

    # Verify abc_docs_pusher gets the correct docs in changes feed
    verify_changes(abc_doc_pusher, expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=abc_doc_pusher.cache)

    # Verify docs from seth continous changes is the same as abc_docs_pusher's docs
    verify_same_docs(expected_num_docs=num_docs, doc_dict_one=docs_in_changes, doc_dict_two=abc_doc_pusher.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


def test_longpoll_changes_sanity(conf, num_docs, num_revisions):

    log.info("conf: {}".format(conf))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=testkit.settings.MAX_REQUEST_WORKERS) as executor:

        futures = dict()
        futures[executor.submit(seth.start_longpoll_changes_tracking, termination_doc_id="killpolling")] = "polling"
        futures[executor.submit(abc_doc_pusher.add_docs, num_docs)] = "doc_pusher"

        for future in concurrent.futures.as_completed(futures):
            task_name = futures[future]

            # Send termination doc to seth long poller
            if task_name == "doc_pusher":
                abc_doc_pusher.update_docs(num_revs_per_doc=num_revisions)

                # Allow time for changes to reach subscribers
                time.sleep(5)

                doc_terminator.add_doc("killpolling")
            elif task_name == "polling":
                docs_in_changes, seq_num = future.result()

    # Verify abc_docs_pusher gets the correct docs in changes feed
    verify_changes(abc_doc_pusher, expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=abc_doc_pusher.cache)

    # Verify docs from seth continous changes is the same as abc_docs_pusher's docs
    verify_same_docs(expected_num_docs=num_docs, doc_dict_one=docs_in_changes, doc_dict_two=abc_doc_pusher.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)
