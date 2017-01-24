import time
import pytest

import concurrent.futures
import requests.exceptions

import libraries.testkit.settings
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes
from libraries.testkit.verify import verify_same_docs

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient

from keywords import document
from keywords import userinfo


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_docs, num_revisions", [
    ("sync_gateway_default_functional_tests", 5000, 1),
    ("sync_gateway_default_functional_tests", 50, 100)
])
def test_longpoll_changes_parametrized(params_from_base_test_setup, sg_conf_name, num_docs, num_revisions):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running: 'longpoll_changes_parametrized': {}".format(cluster_conf))
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=libraries.testkit.settings.MAX_REQUEST_WORKERS) as executor:

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


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_docs, num_revisions", [
    ("sync_gateway_default_functional_tests", 10, 10),
])
def test_longpoll_changes_sanity(params_from_base_test_setup, sg_conf_name, num_docs, num_revisions):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running: 'longpoll_changes_sanity': {}".format(cluster_conf))
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    admin = Admin(cluster.sync_gateways[0])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["ABC", "TERMINATE"])
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    doc_terminator = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_terminator", password="password", channels=["TERMINATE"])

    docs_in_changes = dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=libraries.testkit.settings.MAX_REQUEST_WORKERS) as executor:

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


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_longpoll_awaken_doc_add_update(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    adam_user_info = userinfo.UserInfo(name="adam", password="Adampass1", channels=["NBC"], roles=[])
    traun_user_info = userinfo.UserInfo(name="traun", password="Traunpass1", channels=["CBS"], roles=[])
    andy_user_info = userinfo.UserInfo(name="andy", password="Andypass1", channels=["MTV"], roles=[])
    sg_db = "db"

    client = MobileRestClient()

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=adam_user_info.name, password=adam_user_info.password, channels=adam_user_info.channels)

    traun_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=traun_user_info.name, password=traun_user_info.password, channels=traun_user_info.channels)

    andy_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=andy_user_info.name, password=andy_user_info.password, channels=andy_user_info.channels)

    # Get starting sequence of docs, use the last seq to progress past any _user docs.
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=andy_auth)

    # Make sure _user docs shows up in the changes feed
    assert len(adam_changes["results"]) == 1 and adam_changes["results"][0]["id"] == "_user/adam"
    assert len(traun_changes["results"]) == 1 and traun_changes["results"][0]["id"] == "_user/traun"
    assert len(andy_changes["results"]) == 1 and andy_changes["results"][0]["id"] == "_user/andy"

    with concurrent.futures.ProcessPoolExecutor() as ex:
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=30, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=30, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=30, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Add 3 docs with adam auth, one with adam channels, one with traun channels, one with andy auth
        # Tests the changes feed wakes up for user created docs and non user created docs
        adam_add_doc_task_1 = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                        number=1, id_prefix="adam_doc",
                                        auth=adam_auth, channels=adam_user_info.channels)

        adam_add_doc_task_2 = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                        number=1, id_prefix="traun_doc",
                                        auth=adam_auth, channels=traun_user_info.channels)

        adam_add_doc_task_3 = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                        number=1, id_prefix="andy_doc",
                                        auth=adam_auth, channels=andy_user_info.channels)

        # Wait for docs adds to complete
        adam_doc_1 = adam_add_doc_task_1.result()
        assert len(adam_doc_1) == 1

        adam_doc_2 = adam_add_doc_task_2.result()
        assert len(adam_doc_2) == 1

        adam_doc_3 = adam_add_doc_task_3.result()
        assert len(adam_doc_3) == 1

        # Assert that the changes feed woke up and that the doc change was propagated
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "adam_doc_0"

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "traun_doc_0"

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "andy_doc_0"

        # Start another longpoll changes request
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Check to see that doc updates to own user doc wake up changes feed
        adam_update_docs_task = ex.submit(client.update_docs, url=sg_url, db=sg_db, docs=adam_doc_1, number_updates=1, auth=adam_auth)
        traun_update_docs_task = ex.submit(client.update_docs, url=sg_url, db=sg_db, docs=adam_doc_2, number_updates=1, auth=traun_auth)
        andy_update_docs_task = ex.submit(client.update_docs, url=sg_url, db=sg_db, docs=adam_doc_3, number_updates=1, auth=andy_auth)

        # Wait for docs updates to complete
        adam_updated_docs = adam_update_docs_task.result()
        assert len(adam_updated_docs) == 1
        assert adam_updated_docs[0]["rev"].startswith("2-")

        traun_updated_docs = traun_update_docs_task.result()
        assert len(traun_updated_docs) == 1
        assert traun_updated_docs[0]["rev"].startswith("2-")

        andy_updated_docs = andy_update_docs_task.result()
        assert len(andy_updated_docs) == 1
        assert andy_updated_docs[0]["rev"].startswith("2-")

        # Assert that the changes feed woke up and that the doc updates was propagated
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "adam_doc_0"
        rev_from_change = int(adam_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "traun_doc_0"
        rev_from_change = int(traun_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "andy_doc_0"
        rev_from_change = int(andy_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2

        # Start another longpoll changes request from the last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Add doc with access to all channels
        adam_add_doc_task_4 = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                        number=1, id_prefix="all_doc",
                                        auth=adam_auth,
                                        channels=adam_user_info.channels + traun_user_info.channels + andy_user_info.channels)

        all_doc = adam_add_doc_task_4.result()
        assert len(all_doc) == 1

        # Assert that the changes feed woke up and that the doc add was propagated to all users
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(adam_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 1

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(traun_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 1

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(andy_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 1

        # Start another longpoll changes request from the last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Update doc with access to all channels
        adam_update_docs_task_2 = ex.submit(client.update_docs, url=sg_url, db=sg_db, docs=all_doc, number_updates=1, auth=adam_auth)

        # Wait for docs updates to complete
        all_doc_updated = adam_update_docs_task_2.result()
        assert len(all_doc_updated) == 1
        assert all_doc_updated[0]["rev"].startswith("2-")

        # Assert that the changes feed woke up and that the doc update was propagated to all users
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(adam_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(traun_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "all_doc_0"
        rev_from_change = int(andy_changes["results"][0]["changes"][0]["rev"].split("-")[0])
        assert rev_from_change == 2


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_longpoll_awaken_channels(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    adam_user_info = userinfo.UserInfo(name="adam", password="Adampass1", channels=["NBC", "ABC"], roles=[])
    traun_user_info = userinfo.UserInfo(name="traun", password="Traunpass1", channels=[], roles=[])
    andy_user_info = userinfo.UserInfo(name="andy", password="Andypass1", channels=[], roles=[])
    sg_db = "db"
    doc_id = "adam_doc_0"

    client = MobileRestClient()

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=adam_user_info.name, password=adam_user_info.password, channels=adam_user_info.channels)

    traun_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=traun_user_info.name, password=traun_user_info.password, channels=traun_user_info.channels)

    andy_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=andy_user_info.name, password=andy_user_info.password, channels=andy_user_info.channels)

    ############################################################
    # changes feed wakes with Channel Access via Admin API
    ############################################################

    # Get starting sequence of docs, use the last seq to progress past any _user docs.
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=andy_auth)

    # Make sure _user docs shows up in the changes feed
    assert len(adam_changes["results"]) == 1 and adam_changes["results"][0]["id"] == "_user/adam"
    assert len(traun_changes["results"]) == 1 and traun_changes["results"][0]["id"] == "_user/traun"
    assert len(andy_changes["results"]) == 1 and andy_changes["results"][0]["id"] == "_user/andy"

    with concurrent.futures.ProcessPoolExecutor() as ex:

        # Start changes feed for 3 users
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Add add a doc for adam with "NBC" and "ABC" channels
        # Add one doc, this should wake up the changes feed
        adam_add_docs_task = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                       number=1, id_prefix="adam_doc",
                                       auth=adam_auth, channels=adam_user_info.channels)

        # Wait for docs adds to complete
        adam_docs = adam_add_docs_task.result()
        assert len(adam_docs) == 1

        # Assert that the changes feed woke up and that the doc change was propagated
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == doc_id

        # Verify that the changes feed is still listening for Traun and Andy
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Update the traun and andy to have one of adam's channels
        update_traun_user_task = ex.submit(client.update_user, url=sg_admin_url, db=sg_db,
                                           name=traun_user_info.name, password=traun_user_info.password, channels=["NBC"])
        traun_auth = update_traun_user_task.result()

        update_andy_user_task = ex.submit(client.update_user, url=sg_admin_url, db=sg_db,
                                          name=andy_user_info.name, password=andy_user_info.password, channels=["ABC"])
        andy_auth = update_andy_user_task.result()

        # Make sure changes feed wakes up and contains at least one change, 2 may be possible if the _user doc is included
        # Make sure the first change is 'adam_doc'
        traun_changes = traun_changes_task.result()
        assert 1 <= len(traun_changes["results"]) <= 2
        assert traun_changes["results"][0]["id"] == "adam_doc_0" or traun_changes["results"][0]["id"] == "_user/traun"

        andy_changes = andy_changes_task.result()
        assert 1 <= len(andy_changes["results"]) <= 2
        assert andy_changes["results"][0]["id"] == "adam_doc_0" or andy_changes["results"][0]["id"] == "_user/andy"

    # Block until user docs are seen
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/adam", auth=adam_auth)
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/traun", auth=traun_auth)
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/andy", auth=andy_auth)

    # Make sure that adams doc shows up in changes due to the fact that the changes feed may be woken up with a _user doc above
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=adam_docs, auth=adam_auth)
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=adam_docs, auth=traun_auth)
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=adam_docs, auth=andy_auth)

    ############################################################
    # changes feed wakes with Channel Removal via Sync function
    ############################################################

    # Get latest last_seq for next test section
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=andy_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:

        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Remove the channels property from the doc
        client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=traun_auth, channels=[])

        # All three changes feeds should wake up and return one result
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["removed"] == ["ABC", "NBC"]

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["removed"] == ["NBC"]

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["removed"] == ["ABC"]

    # Verify that users no longer can access the doc
    for user_auth in [adam_auth, traun_auth, andy_auth]:
        with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=user_auth)
        assert "403 Client Error: Forbidden for url:" in excinfo.value.message

    ############################################################
    # changes feed wakes with Channel Grant via Sync function
    ############################################################

    # Get latest last_seq for next test section
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=andy_auth)

    admin_auth = client.create_user(url=sg_admin_url, db=sg_db, name="admin", password="password", channels=["admin"])

    channel_grant_doc_id = "channel_grant_with_doc_intially"

    # Add another doc with no channels
    channel_grant_doc_body = document.create_doc(doc_id=channel_grant_doc_id, channels=["admin"])
    client.add_doc(url=sg_url, db=sg_db, doc=channel_grant_doc_body, auth=admin_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # update the grant doc to have channel for all users
        update_task = ex.submit(client.update_doc, url=sg_url, db=sg_db, doc_id=channel_grant_doc_id, auth=admin_auth, channels=["admin", "ABC", "NBC"])
        updated_doc = update_task.result()
        assert updated_doc["rev"].startswith("2-")

        # Verify that access grant wakes up changes feed for adam, traun, and Andy
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "channel_grant_with_doc_intially"
        assert adam_changes["results"][0]["changes"][0]["rev"].startswith("2-")

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "channel_grant_with_doc_intially"
        assert traun_changes["results"][0]["changes"][0]["rev"].startswith("2-")

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "channel_grant_with_doc_intially"
        assert andy_changes["results"][0]["changes"][0]["rev"].startswith("2-")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_longpoll_awaken_roles(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    admin_role = "admin_role"
    admin_channel = "admin_channel"

    admin_user_info = userinfo.UserInfo(name="admin", password="pass", channels=[], roles=[admin_role])
    adam_user_info = userinfo.UserInfo(name="adam", password="Adampass1", channels=[], roles=[])
    traun_user_info = userinfo.UserInfo(name="traun", password="Traunpass1", channels=[], roles=[])
    andy_user_info = userinfo.UserInfo(name="andy", password="Andypass1", channels=[], roles=[])
    sg_db = "db"

    client = MobileRestClient()

    # Create a role on sync_gateway
    client.create_role(url=sg_admin_url, db=sg_db, name=admin_role, channels=[admin_channel])

    # Create users with no channels or roles
    admin_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=admin_user_info.name, password=admin_user_info.password, roles=[admin_role])

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=adam_user_info.name, password=adam_user_info.password)

    traun_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=traun_user_info.name, password=traun_user_info.password)

    andy_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=andy_user_info.name, password=andy_user_info.password)

    ################################
    # change feed wakes for role add
    ################################

    # Get starting sequence of docs, use the last seq to progress past any _user docs.
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="longpoll", auth=andy_auth)

    # Make sure _user docs shows up in the changes feed
    assert len(adam_changes["results"]) == 1 and adam_changes["results"][0]["id"] == "_user/adam"
    assert len(traun_changes["results"]) == 1 and traun_changes["results"][0]["id"] == "_user/traun"
    assert len(andy_changes["results"]) == 1 and andy_changes["results"][0]["id"] == "_user/andy"

    # Add doc with channel associated with the admin role
    admin_doc = client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="admin_doc", auth=admin_auth, channels=[admin_channel])
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=admin_doc, auth=admin_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        adam_auth = client.update_user(url=sg_admin_url, db=sg_db,
                                       name=adam_user_info.name, password=adam_user_info.password, roles=[admin_role])

        traun_auth = client.update_user(url=sg_admin_url, db=sg_db,
                                        name=traun_user_info.name, password=traun_user_info.password, roles=[admin_role])

        andy_auth = client.update_user(url=sg_admin_url, db=sg_db,
                                       name=andy_user_info.name, password=andy_user_info.password, roles=[admin_role])

        adam_changes = adam_changes_task.result()
        assert 1 <= len(adam_changes["results"]) <= 2
        assert adam_changes["results"][0]["id"] == "admin_doc_0" or adam_changes["results"][0]["id"] == "_user/adam"

        traun_changes = traun_changes_task.result()
        assert 1 <= len(traun_changes["results"]) <= 2
        assert traun_changes["results"][0]["id"] == "admin_doc_0" or traun_changes["results"][0]["id"] == "_user/traun"

        andy_changes = andy_changes_task.result()
        assert 1 <= len(andy_changes["results"]) <= 2
        assert andy_changes["results"][0]["id"] == "admin_doc_0" or andy_changes["results"][0]["id"] == "_user/andy"

    # Check that the user docs all show up in changes feed
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/adam", auth=adam_auth)
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/traun", auth=traun_auth)
    client.verify_doc_id_in_changes(url=sg_url, db=sg_db, expected_doc_id="_user/andy", auth=andy_auth)

    # Check that the admin doc made it to all the changes feeds
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=admin_doc, auth=adam_auth)
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=admin_doc, auth=traun_auth)
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=admin_doc, auth=andy_auth)

    # At this point, each user should have a changes feed that is caught up for the next section

    ###########################################
    # change feed wakes for channel add to role
    ###########################################

    abc_channel = "ABC"
    abc_pusher_info = userinfo.UserInfo(name="abc_pusher", password="pass", channels=[abc_channel], roles=[])

    abc_pusher_auth = client.create_user(url=sg_admin_url, db=sg_db, name=abc_pusher_info.name,
                                         password=abc_pusher_info.password, channels=abc_pusher_info.channels)

    # Add doc with ABC channel
    client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="abc_doc", auth=abc_pusher_auth, channels=[abc_channel])

    # Get latest last_seq for next test section
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=andy_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Update admin role to include ABC channel
        # Since adam, traun, and andy are assigned to that role, they should wake up and get the 'abc_pusher_0' doc
        client.update_role(url=sg_admin_url, db=sg_db, name=admin_role, channels=[admin_channel, abc_channel])

        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "abc_doc_0"

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "abc_doc_0"

        andy_changes = adam_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "abc_doc_0"


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/wake_changes_access",
])
def test_longpoll_awaken_via_sync_access(params_from_base_test_setup, sg_conf_name):
    """
    Test that longpoll changes feed wakes up on access() in sync_function

    The contrived sync_function below is used:
        function(doc, oldDoc){
            if(doc._id == "access_doc_0") {
                console.log("granting_access!");
                access(["adam", "traun", "andy"], "NATGEO");
            }
            channel(doc, doc.channels);
        }
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    sg_db = "db"

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    client = MobileRestClient()

    channel_pusher_info = userinfo.UserInfo(name="channel_pusher", password="pass", channels=["NATGEO"], roles=[])

    adam_user_info = userinfo.UserInfo(name="adam", password="Adampass1", channels=[], roles=[])
    traun_user_info = userinfo.UserInfo(name="traun", password="Traunpass1", channels=[], roles=[])
    andy_user_info = userinfo.UserInfo(name="andy", password="Andypass1", channels=[], roles=[])

    channel_pusher_auth = client.create_user(url=sg_admin_url,
                                             db=sg_db,
                                             name=channel_pusher_info.name,
                                             password=channel_pusher_info.password,
                                             channels=channel_pusher_info.channels)

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db, name=adam_user_info.name, password=adam_user_info.password)
    traun_auth = client.create_user(url=sg_admin_url, db=sg_db, name=traun_user_info.name, password=traun_user_info.password)
    andy_auth = client.create_user(url=sg_admin_url, db=sg_db, name=andy_user_info.name, password=andy_user_info.password)

    client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="natgeo", channels=["NATGEO"], auth=channel_pusher_auth)

    # Get starting sequence of docs, use the last seq to progress past any _user docs.
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=andy_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Grant adam, traun and andy access to the "NATGEO" channel
        client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="access_doc", channels=[], auth=channel_pusher_auth)

        # Changes feed should wake up with the natgeo_0 doc
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "natgeo_0"

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "natgeo_0"

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "natgeo_0"

    # Assert that the changes are caught up and should recieve no new changes from last_seq
    # Test for https://github.com/couchbase/sync_gateway/issues/2186
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=adam_changes["last_seq"], auth=adam_auth, timeout=1)
    assert len(adam_changes["results"]) == 0

    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=traun_changes["last_seq"], auth=traun_auth, timeout=1)
    assert len(traun_changes["results"]) == 0

    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=andy_changes["last_seq"], auth=andy_auth, timeout=1)
    assert len(andy_changes["results"]) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/wake_changes_roles",
])
def test_longpoll_awaken_via_sync_role(params_from_base_test_setup, sg_conf_name):
    """
    Test that longpoll changes feed wakes up on role() in sync_function

    The contrived sync_function below is used:
        function(doc, oldDoc){
            if(doc._id == "role_doc_0") {
                console.log("granting_access!");
                role(["adam", "traun", "andy"], "role:techno");
            }
            channel(doc, doc.channels);
        }
    """

    cluster_conf = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    sg_db = "db"
    techno_role = "techno"
    techno_channel = "aphex"
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    client = MobileRestClient()

    client.create_role(url=sg_admin_url, db=sg_db, name=techno_role, channels=[techno_channel])
    admin_user_info = userinfo.UserInfo(name="admin", password="pass", channels=[], roles=[techno_role])

    adam_user_info = userinfo.UserInfo(name="adam", password="Adampass1", channels=[], roles=[])
    traun_user_info = userinfo.UserInfo(name="traun", password="Traunpass1", channels=[], roles=[])
    andy_user_info = userinfo.UserInfo(name="andy", password="Andypass1", channels=[], roles=[])

    admin_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=admin_user_info.name, password=admin_user_info.password, roles=adam_user_info.roles)

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=adam_user_info.name, password=adam_user_info.password)

    traun_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=traun_user_info.name, password=traun_user_info.password)

    andy_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=andy_user_info.name, password=andy_user_info.password)

    client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="techno_doc", channels=[techno_channel], auth=admin_auth)

    # Get starting sequence of docs, use the last seq to progress past any _user docs.
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, feed="normal", auth=andy_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        # Start changes feed for 3 users from latest last_seq
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=10, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=10, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=10, auth=andy_auth)

        # Wait for changes feed to notice there are no changes and enter wait. 2 seconds should be more than enough
        time.sleep(2)

        # Make sure the changes future is still running and has not exited due to any new changes, the feed should be caught up
        # and waiting
        assert not adam_changes_task.done()
        assert not traun_changes_task.done()
        assert not andy_changes_task.done()

        # Grant adam, traun and andy access to the "NATGEO" channel
        client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="role_doc", channels=[], auth=admin_auth)

        # Changes feed should wake up with the natgeo_0 doc
        adam_changes = adam_changes_task.result()
        assert len(adam_changes["results"]) == 1
        assert adam_changes["results"][0]["id"] == "techno_doc_0"
        assert adam_changes["results"][0]["changes"][0]["rev"].startswith("1-")

        traun_changes = traun_changes_task.result()
        assert len(traun_changes["results"]) == 1
        assert traun_changes["results"][0]["id"] == "techno_doc_0"
        assert traun_changes["results"][0]["changes"][0]["rev"].startswith("1-")

        andy_changes = andy_changes_task.result()
        assert len(andy_changes["results"]) == 1
        assert andy_changes["results"][0]["id"] == "techno_doc_0"
        assert andy_changes["results"][0]["changes"][0]["rev"].startswith("1-")

    # Assert that the changes are caught up and should recieve no new changes from last_seq
    # Test for https://github.com/couchbase/sync_gateway/issues/2186
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=adam_changes["last_seq"], auth=adam_auth, timeout=1)
    assert len(adam_changes["results"]) == 0

    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=traun_changes["last_seq"], auth=traun_auth, timeout=1)
    assert len(traun_changes["results"]) == 0

    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=andy_changes["last_seq"], auth=andy_auth, timeout=1)
    assert len(andy_changes["results"]) == 0
