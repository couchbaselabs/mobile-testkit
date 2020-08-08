import pytest
import time
import random
from sys import maxsize
from threading import Thread
import os
import pdb


from libraries.testkit import cluster

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from libraries.data.doc_generators import simple, four_k, simple_user, complex_doc
from datetime import datetime, timedelta
from CBLClient.Utils import Utils
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway


def reconfig_sync_gateway_clusters(params_from_base_suite_setup, sg_conf_name='listener_tests/multiple_sync_gateways'):
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_mode = params_from_base_suite_setup["mode"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]

    cluster_obj = cluster.Cluster(config=cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    cluster_obj.reset(sg_config_path=sg_config)

    sg1 = cluster_obj.sync_gateways[0]
    sg2 = cluster_obj.sync_gateways[1]

    sgw_obj = SyncGateway()

    sgw_cluster1_sg_config_name = "listener_tests/sg_replicate_sgw_cluster1"
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_sg_config_name, sg_mode)
    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)
    sgw_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg1.ip,
                                         sync_gateway_version=sync_gateway_version, enable_import=True)

    sgw_cluster2_sg_config_name = "listener_tests/sg_replicate_sgw_cluster2"
    sgw_cluster2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_sg_config_name, sg_mode)
    sgw_cluster2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_sg_config)
    sgw_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster2_config_path, url=sg2.ip,
                                         sync_gateway_version=sync_gateway_version, enable_import=True)

    print("done with reconfig sync gateway here")
    return sg1, sg2


@pytest.mark.listener
@pytest.mark.replication
def test_system(params_from_base_suite_setup):
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_url_list = params_from_base_suite_setup["sg_url_list"]
    sg_db_list = params_from_base_suite_setup["sg_db_list"]
    sg_blip_url_list = params_from_base_suite_setup["target_url_list"]
    sg_admin_url_list = params_from_base_suite_setup["sg_admin_url_list"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    query_obj_list = params_from_base_suite_setup["query_obj_list"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    resume_cluster = params_from_base_suite_setup["resume_cluster"]
    generator = params_from_base_suite_setup["generator"]
    enable_rebalance = params_from_base_suite_setup["enable_rebalance"]
    num_of_docs = params_from_base_suite_setup["num_of_docs"]
    num_of_doc_updates = params_from_base_suite_setup["num_of_doc_updates"]
    num_of_docs_to_update = params_from_base_suite_setup["num_of_docs_to_update"]
    num_of_docs_in_itr = params_from_base_suite_setup["num_of_docs_in_itr"]
    num_of_docs_to_delete = params_from_base_suite_setup["num_of_docs_to_delete"]
    num_of_docs_to_add = params_from_base_suite_setup["num_of_docs_to_add"]
    up_time = params_from_base_suite_setup["up_time"]
    repl_status_check_sleep_time = params_from_base_suite_setup["repl_status_check_sleep_time"]
    platform_list = params_from_base_suite_setup["platform_list"]

    if sync_gateway_version < "2.7.0":
        pytest.skip('This test cannot run with sg version below 2.8.0')

    # Create CBL database
    sg_client = MobileRestClient()

    channels_sg_list = [['channel_sg1'], ['channel_sg2']]
    username_list = ["autotest1", "autotest2"]
    password = "password"

    cur_cluster = Cluster(config=cluster_config)
    if enable_rebalance:
        if len(cur_cluster.servers) < 2:
            raise Exception("Please provide at least 3 servers")

        server_urls = []
        for server in cur_cluster.servers:
            server_urls.append(server.url)
        primary_server = cur_cluster.servers[0]
        servers = cur_cluster.servers[1:]

    doc_id_for_new_docs = num_of_docs
    query_limit = 1000
    query_offset = 0

    doc_ids_list = []
    for k in range(len(cbl_db_list)):
        doc_ids_list.append(set())
    # doc_ids = set()
    docs_per_db = num_of_docs // len(cbl_db_list)  # Equally distributing docs to db
    extra_docs = num_of_docs % len(cbl_db_list)  # Docs left after equal distribution
    num_of_itr_per_db = docs_per_db // num_of_docs_in_itr  # iteration required to add docs in each db
    extra_docs_in_itr_per_db = docs_per_db % num_of_docs_in_itr  # iteration required to add docs leftover docs per db

    sg1, sg2 = reconfig_sync_gateway_clusters(params_from_base_suite_setup)
    if not resume_cluster:
        # Reset cluster to ensure no data in system

        i = 0
        for sg_admin_url, sg_db in zip(sg_admin_url_list, sg_db_list):
            log_info("Using SG ur: {}".format(sg_admin_url))
            sg_client.create_user(sg_admin_url, sg_db, username_list[i % 2], password, channels=channels_sg_list[i % 2])
            i += 1

        i = 0
        for cbl_db, db_obj, db_name, doc_ids in zip(cbl_db_list, db_obj_list, db_name_list, doc_ids_list):
            log_info("Adding doc on {} db".format(db_name))
            doc_prefix = "{}_doc".format(db_name)
            # adding bulk docs to each db
            j = 0
            for j in range(num_of_itr_per_db):
                ids = db_obj.create_bulk_docs(num_of_docs_in_itr, doc_prefix, db=cbl_db, channels=channels_sg_list[i % 2],
                                              id_start_num=j * num_of_docs_in_itr, generator=generator)
                doc_ids.update(ids)
            # adding remaining docs to each db
            if extra_docs_in_itr_per_db != 0:
                ids = db_obj.create_bulk_docs(extra_docs_in_itr_per_db, "cbl{}_{}".format(i, db_name), db=cbl_db,
                                              channels=channels_sg_list[i % 2], id_start_num=(j + 1) * num_of_docs_in_itr,
                                              generator=generator)
                doc_ids.update(ids)
            # add the extra docs to last db
            if extra_docs != 0:
                ids = db_obj.create_bulk_docs(extra_docs, "cbl{}_{}".format(i, db_name), db=cbl_db, channels=channels_sg_list[i % 2],
                                              id_start_num=docs_per_db, generator=generator)
                doc_ids.update(ids)
            doc_ids_list[i] = doc_ids
            i += 1
    else:
        # getting doc ids from the dbs
        # _check_doc_count(db_obj_list, cbl_db_list)
        count = db_obj_list[0].getCount(cbl_db_list[0])
        itr_count = count // query_limit
        if itr_count == 0:
            itr_count = 1
        for _ in range(itr_count):
            existing_docs = db_obj_list[0].getDocIds(cbl_db_list[0], query_limit, query_offset)
            doc_ids.update(existing_docs)
            query_offset += query_limit
        log_info("{} Docs in DB".format(len(doc_ids)))
        query_offset = 0
        try:
            # Precautionary creation of user
            i = 0
            for sg_admin_url, sg_db in zip(sg_admin_url_list, sg_db_list):
                log_info("Using SG ur: {}".format(sg_admin_url))
                sg_client.create_user(sg_admin_url, sg_db, username_list[i % 2], password, channels=channels_sg_list[i % 2])
                i += 1
        except Exception as err:
            log_info("User already exist: {}".format(err))

    time.sleep(5)
    # Configure replication with push_pull for each cbl db to all sgw
    session_list = []
    for k in range(2):
        cookie, session_id = sg_client.create_session(sg_admin_url_list[k], sg_db_list[k], username_list[k], ttl=900000)
        session = cookie, session_id
        session_list.append(session)

    repl_list = []
    replicator_list = []
    i = 0
    for base_url, cbl_db, query, platform in zip(base_url_list, cbl_db_list, query_obj_list, platform_list):
        replicator = Replication(base_url)
        authenticator = Authenticator(base_url)

        cookie = session_list[i % 2][0]
        session_id = session_list[i % 2][1]
        replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
        repl = replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url_list[i %2 ],
                                                  replication_type="push_pull", continuous=True, channels=channels_sg_list[i % 2])

        replicator_list.append(replicator)
        repl_list.append(repl)

        results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
        # Query results do not store in memory for dot net, so no need to release memory for dotnet
        if platform.lower() not in ["net-msft", "uwp", "xamarin-ios", "xamarin-android"]:
            _releaseQueryResults(base_url, results)
        i += 1

    sg_repl_1 = sg1.start_replication2(local_db=sg_db_list[0],
                                       remote_url=sg2.url,
                                       remote_db=sg_db_list[1],
                                       continuous=True,
                                       remote_user=username_list[1],
                                       remote_password=password)
    sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)

    current_time = datetime.now()
    running_time = current_time + timedelta(minutes=up_time)

    # _check_doc_count(db_obj_list, cbl_db_list)
    x = 1
    while running_time - current_time > timedelta(0):
        log_info('*' * 20)
        log_info("Starting iteration no. {} of system testing".format(x))
        log_info('*' * 20)
        x += 1
        if enable_rebalance:
            server = servers[random.randint(0, len(servers) - 1)]
        ######################################
        # Checking for docs update on SG side #
        ######################################
        for k in range(2):
            docs_to_update = _get_random_doc_ids(doc_ids_list, k, num_of_docs_to_update)
            # pdb.set_trace()
            sg_docs = sg_client.get_bulk_docs(url=sg_url_list[k], db=sg_db_list[k], doc_ids=list(docs_to_update), auth=session_list[k])[0]
            for sg_doc in sg_docs:
                sg_doc["id"] = sg_doc["_id"]
            log_info("Updating {} docs on SG - {}".format(len(docs_to_update),
                                                          docs_to_update))
            sg_client.update_docs(url=sg_url_list[k], db=sg_db_list[k], docs=sg_docs,
                                  number_updates=num_of_doc_updates, auth=session_list[k], channels=channels_sg_list[k])

        sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)
        log_info("doc update - sg - update done")
        # Waiting until replicator finishes on all dbs
        m = 0
        for base_url, cbl_db, query, platform in zip(base_url_list,
                                                     cbl_db_list,
                                                     query_obj_list,
                                                     platform_list):
            # inner loop for thread here
            t = Thread(target=_replicaton_status_check, args=(replicator_list[m % 2], repl_list[m % 2], repl_status_check_sleep_time))
            t.start()
            t.join()

            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ["net-msft", "uwp", "xamarin-ios", "xamarin-android"]:
                _releaseQueryResults(base_url, results)
            m += 1

        log_info("doc update - sg - replication done")
        #######################################
        # Checking for doc update on CBL side #
        #######################################
        m = 0
        for base_url, db_obj, cbl_db, query, platform, doc_ids in zip(base_url_list,
                                                                      db_obj_list,
                                                                      cbl_db_list,
                                                                      query_obj_list,
                                                                      platform_list,
                                                                      doc_ids_list):
            docs_to_update = random.sample(doc_ids, num_of_docs_to_update)
            updates_per_db = num_of_docs_to_update // len(db_obj_list)
            if updates_per_db == 0:
                updates_per_db = 1
            log_info("Updating {} docs on {} db - {}".format(updates_per_db,
                                                             db_obj.getName(cbl_db),
                                                             list(docs_to_update)[i: i + updates_per_db]))
            db_obj.update_bulk_docs(cbl_db, num_of_doc_updates, list(docs_to_update)[i: i + updates_per_db])
            i += updates_per_db

            # updating docs will affect all dbs as they are synced with SG.
            t = Thread(target=_replicaton_status_check, args=(replicator_list[m % 2], repl_list[m % 2], repl_status_check_sleep_time))
            t.start()
            t.join()
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ["net-msft", "uwp", "xamarin-ios", "xamarin-android"]:
                _releaseQueryResults(base_url, results)
            m += 1

        sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)
        log_info("doc update - cbl - done")

        ###########################
        # Deleting docs on SG side #
        ###########################
        for k in range(2):
            log_info("delete sg doc ...")
            log_info(k)
            docs_to_delete = set(_get_random_doc_ids(doc_ids_list, k, num_of_docs_to_delete))
            sg_docs = sg_client.get_bulk_docs(url=sg_url_list[k], db=sg_db_list[k], doc_ids=list(docs_to_delete), auth=session_list[k])[0]
            log_info("Deleting {} docs on SG - {}".format(len(docs_to_delete), docs_to_delete))
            # pdb.set_trace()
            sg_client.delete_bulk_docs(url=sg_url_list[k], db=sg_db_list[k], docs=sg_docs, auth=session_list[k])
            doc_ids_list = _remove_docs_to_delete(doc_ids_list, k, docs_to_delete)
            '''
            TODO: verify deleted docs get replicated to another sg
            '''
        sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)
        m = 0
        for base_url, cbl_db, query, platform in zip(base_url_list,
                                                     cbl_db_list,
                                                     query_obj_list,
                                                     platform_list):
            t = Thread(target=_replicaton_status_check, args=(replicator_list[m % 2], repl_list[m % 2], repl_status_check_sleep_time))
            t.start()
            t.join()
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if(platform.lower() != "net-msft" and platform.lower() != "uwp" and platform.lower() != "xamarin-ios" and platform.lower() != "xamarin-android"):
                _releaseQueryResults(base_url, results)
            time.sleep(5)
            m += 1

        if enable_rebalance:
            # Deleting a node from the cluster
            log_info("Rebalance out server: {}".format(server.host))
            primary_server.rebalance_out(server_urls, server)
        log_info("doc delete - sg - done")
        ############################
        # Deleting docs on CBL side #
        ############################
        i = 0
        idx = 0
        for base_url, db_obj, cbl_db, query, platform, doc_ids in zip(base_url_list,
                                                                      db_obj_list,
                                                                      cbl_db_list,
                                                                      query_obj_list,
                                                                      platform_list,
                                                                      doc_ids_list):
            docs_to_delete = set(random.sample(doc_ids, num_of_docs_to_delete))
            docs_to_delete_per_db = len(docs_to_delete) // len(db_obj_list)
            if docs_to_delete_per_db == 0:
                docs_to_delete_per_db = 1
            log_info("deleting {} docs from {} db - {}".format(docs_to_delete_per_db,
                                                               db_obj.getName(cbl_db),
                                                               list(docs_to_delete)[i: i + docs_to_delete_per_db]))
            db_obj.delete_bulk_docs(cbl_db, list(docs_to_delete)[i: i + docs_to_delete_per_db])
            time.sleep(5)
            for doc_to_del in list(docs_to_delete)[i: i + docs_to_delete_per_db]:
                doc_ids_list[idx].remove(doc_to_del)
            i += docs_to_delete_per_db
            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit,
                                                        offset=query_offset)
            # Deleting docs will affect all dbs as they are synced with SG.
            _check_parallel_replication_changes(base_url, cbl_db, query, platform, replicator_list[idx % 2], repl_list[idx % 2],
                                                repl_status_check_sleep_time, query_limit, query_offset)
            idx += 1
        sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)
        if enable_rebalance:
            # Adding the node back to the cluster
            log_info("Adding Server back {}".format(server.host))
            primary_server.add_node(server, services="kv,index,n1ql")
            log_info("Rebalance in server: {}".format(server.host))
            primary_server.rebalance_in(server_urls, server)
        log_info("doc delete - cbl - done")

        #############################
        # Creating docs on CBL side #
        #############################
        idx = 0
        for base_url, db_obj, cbl_db, query, platform in zip(base_url_list,
                                                             db_obj_list,
                                                             cbl_db_list,
                                                             query_obj_list,
                                                             platform_list):
            name = db_obj.getName(cbl_db)
            docs_to_create = ["cbl_{}_{}".format(name, doc_id) for doc_id in range(doc_id_for_new_docs, doc_id_for_new_docs + num_of_docs_to_add)]
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
                data["channels"] = channels_sg_list[idx % 2]
                data["_id"] = doc_id
                added_docs[doc_id] = data
                new_doc_ids.append(doc_id)
            doc_ids.update(new_doc_ids)
            log_info("creating {} docs on {} - {}".format(len(docs_to_create),
                                                          db_obj.getName(cbl_db),
                                                          new_doc_ids))
            db_obj.saveDocuments(cbl_db, added_docs)
            time.sleep(5)

            t = Thread(target=_replicaton_status_check, args=(replicator_list[idx % 2], repl_list[idx % 2], repl_status_check_sleep_time))
            t.start()
            t.join()

            results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit,
                                                        offset=query_offset)
            # Query results do not store in memory for dot net, so no need to release memory for dotnet
            if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
                _releaseQueryResults(base_url, results)
            idx += 1
            time.sleep(5)
        sg1.admin.wait_until_sgw_replication_done(db=sg_db_list[0], repl_id=sg_repl_1)
        doc_id_for_new_docs += num_of_docs_to_add
        # _check_doc_count(db_obj_list, cbl_db_list)

        current_time = datetime.now()
    # stopping replication
    log_info("Test completed. Stopping Replicators")

    for replicator, repl in zip(replicator_list, repl_list):
        replicator.stop(repl)
        time.sleep(5)
    # _check_doc_count(db_obj_list, cbl_db_list)


def _replicaton_status_check(repl_obj, replicator, repl_status_check_sleep_time=2):
    repl_obj.wait_until_replicator_idle(replicator, max_times=maxsize, sleep_time=repl_status_check_sleep_time)
    total = repl_obj.getTotal(replicator)
    completed = repl_obj.getCompleted(replicator)
    log_info("total: {}".format(total))
    log_info("completed: {}".format(completed))
    # assert total == completed, "total is not equal to completed"


def _check_doc_count(db_obj_list, cbl_db_list):
    new_docs_count = set([db_obj.getCount(cbl_db) for db_obj, cbl_db in zip(db_obj_list, cbl_db_list)])
    log_info("Doc count is - {}".format(new_docs_count))
    if len(new_docs_count) != 1:
        assert 0, "Doc count in all DBs are not equal"


def _check_parallel_replication_changes(base_url, cbl_db, query, platform, repl_obj, repl,
                                        repl_status_check_sleep_time, query_limit, query_offset):
    t = Thread(target=_replicaton_status_check, args=(repl_obj, repl, repl_status_check_sleep_time))
    t.start()
    t.join()

    results = query.query_get_docs_limit_offset(cbl_db, limit=query_limit, offset=query_offset)
    # Query results do not store in memory for dot net, so no need to release memory for dotnet
    if platform.lower() not in ("net-msft", "uwp", "xamarin-ios", "xamarin-android"):
        _releaseQueryResults(base_url, results)


def _releaseQueryResults(base_url, results):
    utils = Utils(base_url)
    utils.release(results)


def _get_random_doc_ids(doc_ids_list, sg_idx, num_of_docs_to_pick):
    participating_docs = set()
    c = len(doc_ids_list)
    for i in range(c):
        if (i % 2 == sg_idx):
            participating_docs = participating_docs | doc_ids_list[i]

    return random.sample(participating_docs, num_of_docs_to_pick)


def _remove_docs_to_delete(doc_ids_list, sg_idx, docs_to_delete):
    c = len(doc_ids_list)
    for i in range(c):
        if (i % 2 == sg_idx):
            for doc in docs_to_delete:
                if doc in doc_ids_list[i]:
                    doc_ids_list[i].remove(doc)

    return doc_ids_list
