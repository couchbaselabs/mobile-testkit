import pytest
import time
import random
from threading import Thread

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication

from libraries.testkit import cluster
from libraries.data.doc_generators import simple, four_k, simple_user,\
    complex_doc
from datetime import datetime, timedelta


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs, num_of_updates, num_of_docs_to_update, num_of_docs_in_itr, num_of_doc_to_delete, num_of_docs_to_add, up_time", [
#     (500000, 10, 100, 10000, 100, 50, 4 * 60),
    (500, 5, 10, 5, 10, 10, 1 * 20),
])
def test_system(params_from_base_suite_setup, num_of_docs, num_of_updates, num_of_docs_to_update, num_of_docs_in_itr, num_of_doc_to_delete, num_of_docs_to_add, up_time):
    sg_db = "db"
    sg_url = params_from_base_suite_setup["sg_url"]
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_blip_url = params_from_base_suite_setup["target_url"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    sg_config = params_from_base_suite_setup["sg_config"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    query_obj_list = params_from_base_suite_setup["query_obj_list"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    resume_cluster = params_from_base_suite_setup["resume_cluster"]
    generator = params_from_base_suite_setup["generator"]
    doc_id_for_new_docs = num_of_docs
    query_limit = 1000
    query_offset = 0

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"

    # Create CBL database
    sg_client = MobileRestClient()

    doc_ids = set()
    docs_per_db = num_of_docs / len(cbl_db_list)  # Equally distributing docs to db
    extra_docs = num_of_docs % len(cbl_db_list)  # Docs left after equal distribution
    num_of_itr_per_db = docs_per_db / num_of_docs_in_itr  # iteration required to add docs in each db
    extra_docs_in_itr_per_db = docs_per_db % num_of_docs_in_itr  # iteration required to add docs leftover docs per db

    c = cluster.Cluster(config=cluster_config)
    if not resume_cluster:
        # Reset cluster to ensure no data in system
        c.reset(sg_config_path=sg_config)
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)

        # adding bulk docs to each db
        for cbl_db, db_obj, db_name in zip(cbl_db_list, db_obj_list, db_name_list):
            print "Adding doc on {} db".format(db_name)
            doc_prefix = "cbl_{}".format(db_name)
            j = 0
            for j in range(num_of_itr_per_db):
                ids = db_obj.create_bulk_docs(num_of_docs_in_itr, doc_prefix, db=cbl_db, channels=channels_sg, id_start_num=j * num_of_docs_in_itr,  generator=generator)
                x = ["{}_{}".format(doc_prefix, doc_id) for doc_id in range(j * num_of_docs_in_itr, (j * num_of_docs_in_itr) + num_of_docs_in_itr)]
                assert sorted(ids) == sorted(x)
                doc_ids.update(ids)
            # adding remaining docs to each db
            if extra_docs_in_itr_per_db != 0:
                ids = db_obj.create_bulk_docs(extra_docs_in_itr_per_db, "cbl_{}".format(db_name), db=cbl_db, channels=channels_sg, id_start_num=(j + 1) * num_of_docs_in_itr,  generator=generator)
                x = ["{}_{}".format(doc_prefix, doc_id) for doc_id in range((j + 1) * num_of_docs_in_itr, ((j + 1) * num_of_docs_in_itr) + extra_docs_in_itr_per_db)]
                assert sorted(ids) == sorted(x)
                doc_ids.update(ids)
        # add the extra docs to last db
        if extra_docs != 0:
            ids = db_obj.create_bulk_docs(extra_docs, "cbl_{}".format(db_name), db=cbl_db, channels=channels_sg, id_start_num=docs_per_db,  generator=generator)
            x = ["{}_{}".format(doc_prefix, doc_id) for doc_id in range(docs_per_db, docs_per_db + extra_docs_in_itr_per_db)]
            assert sorted(ids) == sorted(x)
            doc_ids.update(ids)
    else:
        # getting doc ids from the dbs
        _check_doc_count(db_obj_list, cbl_db_list)
        count = db_obj_list[0].getCount(cbl_db_list[0])
        itr_count = count / query_limit + 1
        for num in range(itr_count):
            existing_docs= db_obj_list[0].getDocIds(cbl_db_list[0], query_limit, (num + 1) * query_offset)
            doc_ids.update(existing_docs)
            query_offset += query_limit
        print "{} Docs in DB - {}".format(len(doc_ids), doc_ids)
        query_offset = 0

    # Configure replication with push_pull for all db
    replicator_obj_list = []
    replicator_list = []
    for base_url, cbl_db, query in zip(base_url_list, cbl_db_list, query_obj_list):
        repl_obj = Replication(base_url)
        replicator_obj_list.append(repl_obj)
        session, _, repl = repl_obj.create_session_configure_replicate(
            base_url, sg_admin_url, sg_db, username, password, channels_sg, sg_client, cbl_db, sg_blip_url, continuous=True)
        replicator_list.append(repl)
        # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)

    current_time = datetime.now()
    running_time = current_time + timedelta(minutes=up_time)

    _check_doc_count(db_obj_list, cbl_db_list)
    x = 1
    while(running_time - current_time > timedelta(0)):

        print '*' * 20
        print "Starting iteration no. {} of system testing".format(x)
        print '*' * 20
        x += 1
        ######################################
        # Checking for doc update on SG side #
        ######################################
        docs_to_update = random.sample(doc_ids, num_of_docs_to_update)
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]
        sg_docs = [doc for doc in sg_docs if doc["id"] in docs_to_update]
        print "Updating {} docs on SG - {}".format(len(docs_to_update),
                                              docs_to_update)
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs,
                              number_updates=num_of_updates, auth=session, channels=channels_sg)
        
        # Waiting until replicator finishes on all dbs
        for repl_obj, repl, cbl_db, query in zip(replicator_obj_list,
                                                 replicator_list,
                                                 cbl_db_list,
                                                 query_obj_list):
            t = Thread(target=_replicaton_status_check, args=(repl_obj, repl))
            t.start()
            t.join()
            # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)

        # Checking for the no. of docs in all db
#         for db_obj, cbl_db in zip(db_obj_list, cbl_db_list):
#             assert len(doc_ids) == db_obj.getCount(cbl_db)
 
        #######################################
        # Checking for doc update on CBL side #
        #######################################
        docs_to_update = random.sample(doc_ids, num_of_docs_to_update)
        i = 0
        for db_obj, cbl_db, repl_obj, repl, query in zip(db_obj_list,
                                                         cbl_db_list,
                                                         replicator_obj_list,
                                                         replicator_list,
                                                         query_obj_list):
            updates_per_db = len(docs_to_update) / len(db_obj_list)
            print "Updating {} docs on {} db - {}".format(updates_per_db,
                                                     db_obj.getName(cbl_db),
                                                     list(docs_to_update)[i : i + updates_per_db])
            db_obj.update_bulk_docs(cbl_db, num_of_updates, list(docs_to_update)[i : i + updates_per_db])
            i += updates_per_db
            # updating docs will affect all dbs as they are synced with SG.
            t = Thread(target=_replicaton_status_check, args=(repl_obj, repl))
            t.start()
            t.join()
            # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)

        # Checking for the no. of docs in all db
#         for db_obj, cbl_db in zip(db_obj_list, cbl_db_list):
#             assert len(doc_ids) == db_obj.getCount(cbl_db)

        ###########################
        # Deleting doc on SG side #
        ###########################
        docs_to_delete = set(random.sample(doc_ids, num_of_doc_to_delete))
        print "Deleting docs with ids - {}".format(docs_to_delete)
        sg_docs = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=list(docs_to_delete), auth=session)[0]
        print "Deleting {} docs on SG - {}".format(len(docs_to_delete),
                                                   docs_to_delete)
        sg_client.delete_bulk_docs(url=sg_url, db=sg_db,
                                   docs=sg_docs, auth=session)
        for repl_obj, repl, cbl_db, query in zip(replicator_obj_list,
                                                 replicator_list,
                                                 cbl_db_list,
                                                 query_obj_list):
            t = Thread(target=_replicaton_status_check, args=(repl_obj, repl))
            t.start()
            t.join()
            # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)
#             sg_client.delete_bulk_docs(url=sg_url, db=sg_db,
#                                        docs=docs, auth=session)
            time.sleep(5)
        _check_doc_count(db_obj_list, cbl_db_list)
        # removing ids of deleted doc from the list
        doc_ids = doc_ids - docs_to_delete

        ############################
        # Deleting doc on CBL side #
        ############################
        docs_to_delete = set(random.sample(doc_ids, num_of_doc_to_delete))
        print "Deleting {} docs with ids - {}".format(len(docs_to_delete),
                                                      docs_to_delete)
        docs_to_delete_per_db = len(docs_to_delete) / len(db_obj_list)
        i = 0
        for db_obj, cbl_db, repl_obj, repl, query in zip(db_obj_list,
                                                         cbl_db_list,
                                                         replicator_obj_list,
                                                         replicator_list,
                                                         query_obj_list):
            print "deleting {} docs from {} db - {}".format(docs_to_delete_per_db,
                                                       db_obj.getName(cbl_db),
                                                       list(docs_to_delete)[i: i + docs_to_delete_per_db])
            db_obj.delete_bulk_docs(cbl_db, list(docs_to_delete)[i: i + docs_to_delete_per_db])
            i += docs_to_delete_per_db
            time.sleep(5)
            # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)

            # Deleting docs will affect all dbs as they are synced with SG.
            for repl_obj, repl, cbl_db, query in zip(replicator_obj_list,
                                                     replicator_list,
                                                     cbl_db_list,
                                                     query_obj_list):
                t = Thread(target=_replicaton_status_check, args=(repl_obj, repl))
                t.start()
                t.join()
                # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)
        _check_doc_count(db_obj_list, cbl_db_list)
        # removing ids of deleted doc from the list
        doc_ids = doc_ids - docs_to_delete
        # Checking for the no. of docs in all db
#         for db_obj, cbl_db in zip(db_obj_list, cbl_db_list):
#             assert len(doc_ids) == db_obj.getCount(cbl_db)

        #############################
        # Creating docs on CBL side #
        #############################
        for db_obj, cbl_db, repl_obj, repl, query in zip(db_obj_list,
                                                         cbl_db_list,
                                                         replicator_obj_list,
                                                         replicator_list,
                                                         query_obj_list):
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
                data["channels"] = channels_sg
                data["_id"] = doc_id
                added_docs[doc_id] = data
                new_doc_ids.append(doc_id)
            doc_ids.update(new_doc_ids)
            print "creating {} docs on {} - {}".format(len(docs_to_create),
                                                  db_obj.getName(cbl_db),
                                                  new_doc_ids)
            db_obj.saveDocuments(cbl_db, added_docs)
            time.sleep(5)

            # Adding docs will affect all dbs as they are synced with SG.
            t = Thread(target=_replicaton_status_check, args=(repl_obj, repl))
            t.start()
            t.join()
            # query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs / num_of_docs_in_itr, offset=query_offset)
            time.sleep(5)
        doc_id_for_new_docs += num_of_docs_to_add
        _check_doc_count(db_obj_list, cbl_db_list)
            # assert len(doc_ids) == db_obj.getCount(cbl_db)

        current_time = datetime.now()
    # stopping replication
    print "Test completed. Stopping Replicators"
    for repl_obj, repl in zip(replicator_obj_list, replicator_list):
        repl_obj.stop(repl)
        time.sleep(5)
    _check_doc_count(db_obj_list, cbl_db_list)


def _replicaton_status_check(repl_obj, replicator):
        repl_obj.wait_until_replicator_idle(replicator)
        total = repl_obj.getTotal(replicator)
        completed = repl_obj.getCompleted(replicator)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until replication is over

def _check_doc_count(db_obj_list, cbl_db_list):
    new_docs_count = set([db_obj.getCount(cbl_db) for db_obj, cbl_db in zip(db_obj_list, cbl_db_list)])
    print "Doc count is - {}".format(new_docs_count)
    if len(new_docs_count) != 1:
        assert 0, "Doc count in all DBs are not equal"