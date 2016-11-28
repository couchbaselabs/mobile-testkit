import time
import pytest
import collections

import concurrent.futures

import libraries.testkit.settings
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes
from libraries.testkit.verify import verify_same_docs

from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker

UserInfo = collections.namedtuple("UserInfo", ["name", "password", "channels"])

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
    mode = cluster.reset(sg_config_path=sg_conf)

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

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


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
    mode = cluster.reset(sg_config_path=sg_conf)

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

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_longpoll_awaken_doc_add(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]

    mode = params_from_base_test_setup["mode"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_utils = ClusterKeywords()
    cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]

    log_info("Running: 'test_longpoll_awaken_doc_add': {}".format(cluster_conf))
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

    adam_user_info = UserInfo("adam", "Adampass1", ["NBC"])
    traun_user_info = UserInfo("traun", "Traunpass1", ["CBS"])
    andy_user_info = UserInfo("andy", "Andypass1", ["MTV"])
    sg_db = "db"

    client = MobileRestClient()

    adam_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=adam_user_info.name, password=adam_user_info.password, channels=adam_user_info.channels)

    traun_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                    name=traun_user_info.name, password=traun_user_info.password, channels=traun_user_info.channels)

    andy_auth = client.create_user(url=sg_admin_url, db=sg_db,
                                   name=andy_user_info.name, password=andy_user_info.password, channels=andy_user_info.channels)

    # Get starting sequence of docs, use the last seq to progress past any user docs
    adam_changes = client.get_changes(url=sg_url, db=sg_db, since=0, timeout=30, auth=adam_auth)
    traun_changes = client.get_changes(url=sg_url, db=sg_db, since=0, timeout=30, auth=traun_auth)
    andy_changes = client.get_changes(url=sg_url, db=sg_db, since=0, timeout=30, auth=andy_auth)

    with concurrent.futures.ProcessPoolExecutor() as ex:
        adam_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=adam_changes["last_seq"], timeout=30, auth=adam_auth)
        traun_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=traun_changes["last_seq"], timeout=30, auth=traun_auth)
        andy_changes_task = ex.submit(client.get_changes, url=sg_url, db=sg_db, since=andy_changes["last_seq"], timeout=30, auth=andy_auth)

        # make sure longpoll goes to a wait state
        log_info("Sleeping (2 sec) to allow longpoll to enter waiting state ...")
        time.sleep(2)

        # Add one doc, this should wake up the changes feed
        adam_add_docs_task = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                       number=1, id_prefix="adam_doc",
                                       auth=adam_auth, channels=adam_user_info.channels)

        traun_add_docs_task = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                        number=1, id_prefix="traun_doc",
                                        auth=traun_auth, channels=traun_user_info.channels)

        andy_add_docs_task = ex.submit(client.add_docs, url=sg_url, db=sg_db,
                                       number=1, id_prefix="andy_doc",
                                       auth=andy_auth, channels=andy_user_info.channels)

        # Wait for docs adds to complete
        adam_docs = adam_add_docs_task.result()
        assert len(adam_docs) == 1

        traun_docs = traun_add_docs_task.result()
        assert len(traun_docs) == 1

        andy_docs = andy_add_docs_task.result()
        assert len(andy_docs) == 1

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




    # Verify that all changes show up eventually
    # client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=adam_docs, auth=adam_auth)
    # client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=traun_docs, auth=traun_auth)
    # client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=andy_docs, auth=andy_auth)

    import pdb
    pdb.set_trace()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0


