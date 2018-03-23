import pytest
import time
import random

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication

from libraries.testkit import cluster
from libraries.data.doc_generators import simple
from datetime import datetime, timedelta
from CBLClient.Query import Query


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs, num_of_updates, num_of_docs_in_itr, up_time", [
#     (1000000, 10, 10000, 3 * 60),
    (50, 5, 10, 1 * 5),
])
def test_system(params_from_base_test_setup, num_of_docs, num_of_updates, num_of_docs_in_itr, up_time):
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    doc_id_for_new_docs = num_of_docs
    query = Query(base_url)

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')
    channels_sg = ["ABC"]
    username = "autotest"
    password = "password"

    # Create CBL database
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    num_of_itr = num_of_docs / num_of_docs_in_itr
    last_itr_num_docs = num_of_docs % num_of_docs_in_itr
    for i in range(num_of_itr):
        db.create_bulk_docs(num_of_docs_in_itr, "cbl", db=cbl_db, channels=channels_sg, id_start_num=i * num_of_docs_in_itr, generator="complex_doc")
    if last_itr_num_docs != 0:
        db.create_bulk_docs(last_itr_num_docs, "cbl", db=cbl_db, channels=channels_sg, id_start_num=i * num_of_docs_in_itr, generator="complex_doc")
    docs_ids = ["cbl_{}".format(i) for i in range(num_of_docs)]

    # Configure replication with push_pull
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    session, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels_sg, sg_client, cbl_db, sg_blip_url, continuous=True)

    current_time = datetime.now()
    running_time = current_time + timedelta(minutes=up_time)
    range_num = num_of_itr * 10

    while(running_time - current_time > timedelta(0)):
        ########################################
        # Checking for doc update on SG side
        ########################################
        docs_to_update = random.sample(docs_ids, random.randint(0, len(docs_ids) / range_num))
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]
        sg_docs = [doc for doc in sg_docs if doc["id"] in docs_to_update]
        print "updating {} docs on SG".format(len(docs_to_update))
        sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs,
                              number_updates=num_of_updates, auth=session, channels=channels_sg)
 
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until re
        query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs/100, offset=0)
         
 
        #########################################
        # Checking for doc update on CBL side #
        #########################################
        docs_to_update = random.sample(docs_ids, random.randint(1, len(docs_ids) / range_num))
        print "updating {} docs on CBL".format(len(docs_to_update))
        db.update_bulk_docs(cbl_db, 2, docs_to_update)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until re
        query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs/100, offset=0)

        #############################
        # Deleting doc on SG side #
        #############################
        docs_to_delete = random.sample(docs_ids, random.randint(1, len(docs_ids) / range_num))
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)["rows"]
        sg_docs = [doc for doc in sg_docs if doc["id"] in docs_to_delete]
        print "Deleting {} docs on SG".format(len(docs_to_delete))
        sg_client.delete_bulk_docs(url=sg_url, db=sg_db,
                                   docs=sg_docs, auth=session)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until re

        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
        sg_docs = sg_docs["rows"]
        query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs/100, offset=0)

        # Verify database doc counts
#         cbl_doc_count = db.getCount(cbl_db)
#         assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
        docs_ids = [doc_id for doc_id in docs_ids if doc_id not in docs_to_delete]

        ##############################
        # Deleting doc on CBL side #
        ##############################
        docs_to_delete = random.sample(docs_ids, random.randint(1, len(docs_ids) / range_num))
        print "deleting {} docs on CBL".format(len(docs_to_delete))
        db.delete_bulk_docs(cbl_db, docs_to_delete)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until re

        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
        sg_docs = sg_docs["rows"]
        query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs/100, offset=0)

        # Verify database doc counts
#         cbl_doc_count = db.getCount(cbl_db)
#         assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
        docs_ids = [doc_id for doc_id in docs_ids if doc_id not in docs_to_delete]

        ###############################
        # Creating docs on CBL side #
        ###############################
        docs_to_create = ["cbl_{}".format(doc_id) for doc_id in range(doc_id_for_new_docs, doc_id_for_new_docs + range_num)]
        added_docs = {}
        for doc_id in docs_to_create:
            data = simple()
            data["channel"] = channels_sg
            data["_id"] = doc_id
            added_docs[doc_id] = data
        print "creating {} docs on CBL".format(len(docs_to_create))
        db.saveDocuments(cbl_db, added_docs)
        replicator.wait_until_replicator_idle(repl)
        total = replicator.getTotal(repl)
        completed = replicator.getCompleted(repl)
        assert total == completed, "total is not equal to completed"
        time.sleep(5)  # wait until re

        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
        sg_docs = sg_docs["rows"]
        query.query_get_docs_limit_offset(cbl_db, limit=num_of_docs/100, offset=0)

        # Verify database doc counts
#         cbl_doc_count = db.getCount(cbl_db)
#         assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
        doc_id_for_new_docs += range_num

        docs_ids.extend(docs_to_create)
        #docs_ids = db.getDocIds(cbl_db)
        current_time = datetime.now()
    # stopping replication
    replicator.stop(repl)
