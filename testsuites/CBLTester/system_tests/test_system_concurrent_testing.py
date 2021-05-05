import pytest
import time
import random
from sys import maxsize
from threading import Thread
import concurrent.futures

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from libraries.data.doc_generators import simple, four_k, simple_user, complex_doc
from datetime import datetime, timedelta
from CBLClient.Utils import Utils


@pytest.mark.listener
@pytest.mark.replication
def test_system(params_from_base_suite_setup):
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')

    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_config = params_from_base_suite_setup["sg_config"]
    enable_rebalance = params_from_base_suite_setup["enable_rebalance"]

    test_params = dict()
    test_params["num_of_docs"] = params_from_base_suite_setup["num_of_docs"]
    test_params["num_of_docs_in_itr"] = params_from_base_suite_setup["num_of_docs_in_itr"]
    test_params["num_of_itr_per_db"] = test_params["num_of_docs"] // test_params["num_of_docs_in_itr"]  # iteration required to add docs in each db
    test_params["extra_docs_in_itr_per_db"] = test_params["num_of_docs"] % test_params["num_of_docs_in_itr"]  # iteration required to add docs leftover docs per db
    test_params["generator"] = params_from_base_suite_setup["generator"]
    test_params["up_time"] = params_from_base_suite_setup["up_time"]
    test_params["repl_status_check_sleep_time"] = params_from_base_suite_setup["repl_status_check_sleep_time"]
    test_params["num_of_doc_updates"] = params_from_base_suite_setup["num_of_doc_updates"]
    test_params["num_of_docs_to_update"] = params_from_base_suite_setup["num_of_docs_to_update"]
    test_params["num_of_docs_to_delete"] = params_from_base_suite_setup["num_of_docs_to_delete"]
    test_params["num_of_docs_to_add"] = params_from_base_suite_setup["num_of_docs_to_add"]

    sg_params = dict()
    sg_db = "db"
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    sg_params["sg_blip_url"] = params_from_base_suite_setup["target_url"]
    sg_params["sg_url"] = params_from_base_suite_setup["sg_url"]

    base_url_list = params_from_base_suite_setup["base_url_list"]
    testkit_db_obj_list = params_from_base_suite_setup["testkit_db_obj_list"]
    cbl_db_obj_list = params_from_base_suite_setup["cbl_db_obj_list"]
    cbl_db_name_list = params_from_base_suite_setup["cbl_db_name_list"]
    query_obj_list = params_from_base_suite_setup["query_obj_list"]
    platform_list = params_from_base_suite_setup["platform_list"]

    cluster = Cluster(config=cluster_config)
    # if cbs rebalance enabled, require multiple cbs in cluster
    if enable_rebalance:
        if len(cluster.servers) < 2:
            raise Exception("Please provide at least 3 servers")

        server_urls = []
        for server in cluster.servers:
            server_urls.append(server.url)
        primary_server = cluster.servers[0]
        servers = cluster.servers[1:]

    # Reset cluster to ensure no data in system
    cluster.reset(sg_config_path=sg_config)
    sg_client = MobileRestClient()

    _log_system_test("Thread Main", "Test Start", "Using SG url: {}".format(sg_admin_url))
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)

    sg_params["sg_client"] = sg_client
    sg_params["sg_db"] = sg_db
    sg_params["sg_admin_url"] = sg_admin_url
    sg_params["sg_channels"] = channels_sg
    sg_params["username"] = username

    doc_ids_dict = {}
    for db_name in cbl_db_name_list:
        doc_ids_set = set()
        doc_ids_dict[db_name] = doc_ids_set

    # initializing each cbl db, creating specified number of docs to start with
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cbl_db_obj_list)) as executor:
        futures = []
        for cbl_db, db_obj, db_name in zip(cbl_db_obj_list, testkit_db_obj_list, cbl_db_name_list):
            cbl_params = dict()
            cbl_params["cbl_db"] = cbl_db
            cbl_params["db_obj"] = db_obj
            cbl_params["db_name"] = db_name
            futures.append(executor.submit(cbl_db_init, sg_params, cbl_params, test_params))
        i = 0
        for future in concurrent.futures.as_completed(futures):
            _log_system_test("concurrent.futures[{}]".format(i), "cbl_db_init", "completed")
            _log_system_test("concurrent.futures[{}]".format(i), "cbl_db_init", future.result())

            i += 1
            doc_ids_dict.update(future.result())

    time.sleep(5)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cbl_db_obj_list)) as executor:
        futures = []
        for base_url, cbl_db, db_obj, db_name, platform, query in zip(base_url_list, cbl_db_obj_list, testkit_db_obj_list, cbl_db_name_list, platform_list, query_obj_list):
            cbl_params = dict()
            cbl_params["cbl_db"] = cbl_db
            cbl_params["db_obj"] = db_obj
            cbl_params["db_name"] = db_name
            cbl_params["base_url"] = base_url
            cbl_params["platform"] = platform
            cbl_params["query"] = query
            cbl_doc_ids = doc_ids_dict[db_name]
            futures.append(executor.submit(process_per_cbl_client, sg_params, cbl_params, test_params, cbl_doc_ids))
        for future in concurrent.futures.as_completed(futures):
            doc_ids_dict.update(future.result())


def cbl_db_init(sg_params, cbl_params, test_params):
    num_of_itr_per_db = test_params["num_of_itr_per_db"]
    num_of_docs_in_itr = test_params["num_of_docs_in_itr"]
    extra_docs_in_itr_per_db = test_params["extra_docs_in_itr_per_db"]
    generator = test_params["generator"]

    db_name = cbl_params["db_name"]
    db_obj = cbl_params["db_obj"]
    cbl_db = cbl_params["cbl_db"]

    sg_channels = sg_params["sg_channels"]

    thread_name = "Thread {}".format(db_name)
    func_name = "cbl_db_init"

    _log_system_test(thread_name, func_name, "Adding doc on {} db".format(db_name))
    doc_id_set = set()
    doc_prefix = "{}_doc".format(db_name)
    _log_system_test(thread_name, func_name, doc_prefix)
    _log_system_test(thread_name, func_name, num_of_itr_per_db)
    # adding max docs per batch
    for i in range(num_of_itr_per_db):
        ids = db_obj.create_bulk_docs(num_of_docs_in_itr, doc_prefix, db=cbl_db, channels=sg_channels,
                                      id_start_num=i * num_of_docs_in_itr, generator=generator)
        _log_system_test(thread_name, func_name, db_name)
        _log_system_test(thread_name, func_name, ids)
        doc_id_set.update(ids)
    # adding remaining docs
    _log_system_test(thread_name, func_name, "extra")
    _log_system_test(thread_name, func_name, extra_docs_in_itr_per_db)
    if extra_docs_in_itr_per_db != 0:
        ids = db_obj.create_bulk_docs(extra_docs_in_itr_per_db, doc_prefix, db=cbl_db, channels=sg_channels,
                                      id_start_num=(i + 1) * num_of_docs_in_itr, generator=generator)
        _log_system_test(thread_name, func_name, ids)
        doc_id_set.update(ids)

    return {db_name: doc_id_set}


def process_per_cbl_client(sg_params, cbl_params, test_params, doc_ids):
    # run test per cbl db from here 
    query_limit = 1000
    query_offset = 0

    # pulling test specific parameters
    up_time = test_params["up_time"]
    repl_status_check_sleep_time = test_params["repl_status_check_sleep_time"]
    num_of_docs_to_update = test_params["num_of_docs_to_update"]
    num_of_docs_to_delete = test_params["num_of_docs_to_delete"]
    num_of_docs_to_add = test_params["num_of_docs_to_add"]
    doc_id_for_new_docs = test_params["num_of_docs"]
    # num_of_docs = test_params["num_of_docs"]
    # num_of_docs_in_itr = test_params["num_of_docs_in_itr"]
    # num_of_itr_per_db = test_params["num_of_itr_per_db"]
    # extra_docs_in_itr_per_db = test_params["extra_docs_in_itr_per_db"]
    num_of_doc_updates = test_params["num_of_doc_updates"]
    generator = test_params["generator"]

    # pulling sync gateway paramters
    sg_db = sg_params["sg_db"]
    sg_admin_url = sg_params["sg_admin_url"]
    sg_blip_url = sg_params["sg_blip_url"]
    sg_url = sg_params["sg_url"]
    sg_client = sg_params["sg_client"]
    sg_channels = sg_params["sg_channels"]
    username = sg_params["username"]

    # pulling couchbase lite parameters
    base_url = cbl_params["base_url"]
    cbl_db = cbl_params["cbl_db"]
    query = cbl_params["query"]
    db_name = cbl_params["db_name"]
    db_obj = cbl_params["db_obj"]
    platform = cbl_params["platform"]

    thread_name = "Thread {}".format(db_name)

    try:
        repl_obj = Replication(base_url)
        authenticator = Authenticator(base_url)
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username, ttl=900000)
        replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
        session = cookie, session_id
        repl_config = repl_obj.configure(cbl_db, sg_blip_url, continuous=True, channels=sg_channels,
                                         replication_type="push_pull",
                                         replicator_authenticator=replicator_authenticator)
        repl = repl_obj.create(repl_config)
        repl_obj.start(repl)
        repl_obj.wait_until_replicator_idle(repl, max_times=maxsize, sleep_time=repl_status_check_sleep_time)

        current_time = datetime.now()
        running_time = current_time + timedelta(seconds=up_time)
        x = 1
        while running_time - current_time > timedelta(0):

            _log_system_test(thread_name, 'iteration start', '*' * 42)
            _log_system_test(thread_name, 'iteration start', "Starting iteration no. {} of system testing".format(x))
            _log_system_test(thread_name, 'iteration start', '*' * 42)
            x += 1

            #######################################
            # Checking for docs update on SG side #
            #######################################
            docs_to_update = random.sample(doc_ids, num_of_docs_to_update)
            sg_docs = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=list(docs_to_update), auth=session)[0]
            for sg_doc in sg_docs:
                sg_doc["id"] = sg_doc["_id"]
            _log_system_test(thread_name, 'docs update on SG', "Updating {} docs on SG - {}".format(len(docs_to_update), docs_to_update))
            sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs,
                                  number_updates=num_of_doc_updates, auth=session, channels=sg_channels)

            # Waiting until replicator finishes
            _replicaton_status_check(thread_name, repl_obj, repl, repl_status_check_sleep_time)
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)

            #######################################
            # Checking for doc update on CBL side #
            #######################################
            docs_to_update = random.sample(doc_ids, num_of_docs_to_update)
            updates_per_db = len(docs_to_update)
            _log_system_test("Thread {}".format(db_name),
                             "docs update on CBL",
                             "Updating {} docs on {} db - {}".format(updates_per_db, db_obj.getName(cbl_db), list(docs_to_update)))
            db_obj.update_bulk_docs(cbl_db, num_of_doc_updates, list(docs_to_update))

            # updating docs will affect all dbs as they are synced with SG.
            _replicaton_status_check(thread_name, repl_obj, repl, repl_status_check_sleep_time)
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)

            ###########################
            # Deleting docs on SG side #
            ###########################
            docs_to_delete = set(random.sample(doc_ids, num_of_docs_to_delete))
            sg_docs = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=list(docs_to_delete), auth=session)[0]
            _log_system_test("Thread {}".format(db_name),
                             "docs deleting on SG",
                             "Deleting {} docs on SG - {}".format(len(docs_to_delete), docs_to_delete))
            sg_client.delete_bulk_docs(url=sg_url, db=sg_db,
                                       docs=sg_docs, auth=session)

            _replicaton_status_check(thread_name, repl_obj, repl, repl_status_check_sleep_time)
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)
            time.sleep(5)
            # _check_doc_count(db_obj_list, cbl_db_list)
            # removing ids of deleted doc from the list
            doc_ids = doc_ids - docs_to_delete

            ############################
            # Deleting docs on CBL side #
            ############################
            docs_to_delete = set(random.sample(doc_ids, num_of_docs_to_delete))
            docs_to_delete_per_db = len(docs_to_delete)
            _log_system_test("Thread {}".format(db_name),
                             "docs deleting on CBL",
                             "deleting {} docs from {} db - {}".format(docs_to_delete_per_db, db_obj.getName(cbl_db), list(docs_to_delete)))
            db_obj.delete_bulk_docs(cbl_db, list(docs_to_delete))

            time.sleep(5)
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit,
                                                        offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)

            # Deleting docs will affect all dbs as they are synced with SG.
            _check_parallel_replication_changes(thread_name, base_url, repl_obj, repl, cbl_db, query,
                                                repl_status_check_sleep_time, query_limit, platform, query_offset)
            # _check_doc_count(db_obj_list, cbl_db_list)
            # removing ids of deleted doc from the list
            doc_ids = doc_ids - docs_to_delete

            #############################
            # Creating docs on CBL side #
            #############################
            name = db_obj.getName(cbl_db)
            docs_to_create = ["{}_doc_{}".format(name, doc_id) for doc_id in range(doc_id_for_new_docs, doc_id_for_new_docs + num_of_docs_to_add)]
            added_docs = {}
            new_doc_ids = []
            for doc_id in docs_to_create:
                if generator == "complex_doc":
                    data = complex_doc()
                elif generator == "four_k":
                    data = four_k()
                elif generator == "simple_user":
                    data = simple_user()
                else:
                    data = simple()
                data["channels"] = sg_channels
                data["_id"] = doc_id
                added_docs[doc_id] = data
                new_doc_ids.append(doc_id)
            doc_ids.update(new_doc_ids)
            _log_system_test("Thread {}".format(db_name),
                             "docs creating on CBL",
                             "creating {} docs on {} - {}".format(len(docs_to_create), db_obj.getName(cbl_db), new_doc_ids))
            db_obj.saveDocuments(cbl_db, added_docs)
            time.sleep(5)

            _replicaton_status_check(thread_name, repl_obj, repl, repl_status_check_sleep_time)
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit,
                                                        offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)

            time.sleep(5)
            doc_id_for_new_docs += num_of_docs_to_add
            # _check_doc_count(db_obj_list, cbl_db_list)

            current_time = datetime.now()

        # stopping replication
        _log_system_test("Thread {}".format(db_name), "test finishes", "Test completed. Stopping Replicators")

        repl_obj.stop(repl)
        time.sleep(5)
        # _check_doc_count(db_obj_list, cbl_db_list)

        return {db_name: doc_ids}
        # results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
    except (Exception, RuntimeError) as ex:
        _log_system_test(thread_name, "exception caught", ex)
        _log_system_test(thread_name, "quit smoothly")
    finally:
        pass


def _replicaton_status_check(thread_name, repl_obj, replicator, repl_status_check_sleep_time=2):
    repl_obj.wait_until_replicator_idle(replicator, max_times=maxsize, sleep_time=repl_status_check_sleep_time)
    total = repl_obj.getTotal(replicator)
    completed = repl_obj.getCompleted(replicator)
    _log_system_test(thread_name, "_replicaton_status_check", "total: {}".format(total))
    _log_system_test(thread_name, "_replicaton_status_check", "completed: {}".format(completed))
    # assert total == completed, "total is not equal to completed"


def _check_doc_count(db_obj_list, cbl_db_list):
    new_docs_count = set([db_obj.getCount(cbl_db) for db_obj, cbl_db in zip(db_obj_list, cbl_db_list)])
    log_info("Doc count is - {}".format(new_docs_count))
    if len(new_docs_count) != 1:
        assert 0, "Doc count in all DBs are not equal"


def _check_parallel_replication_changes(thread_name, base_url, repl_obj, repl, cbl_db, query,
                                        repl_status_check_sleep_time, query_limit, platform, query_offset):
    _replicaton_status_check(thread_name, repl_obj, repl, repl_status_check_sleep_time)
    results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
    # Query results do not store in memory for dot net, so no need to release memory for dotnet
    if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
        _releaseQueryResults(base_url, results)


def _releaseQueryResults(base_url, results):
    utils = Utils(base_url)
    utils.release(results)


def _log_system_test(tag=None, func=None, message=None):
    log_info("{} || {} || {}".format(tag, func, message))
