import time
import subprocess
import json
import random

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from libraries.testkit import cluster
from keywords.ClusterKeywords import ClusterKeywords
from keywords import couchbaseserver, document
from CBLClient.Document import Document
from concurrent.futures import ThreadPoolExecutor
import pytest


@pytest.mark.transactions
@pytest.mark.syncgateway
@pytest.mark.cbl
def test_transactions_insert_replace_remove_rollback(params_from_base_test_setup):
    '''
    @summary:
    1. Insert a transaction with 3 or more docs
    2. replication from server to SGW and to CBL
    3. Verify all docs in transactions are pulled to CBL
    4. replace the transaction with new content
    5. Verify doc is replicated to cbl whiich commited in transaction
    6. Delete the transaction
    7. Verify doc is removed in cbl
    8. Rollback the transaction
    9. Verify rollback docs are not replicated to cbl
    '''

    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    if not xattrs_enabled:
        pytest.skip('this test require --xattrs flag')
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cluster_servers = topology["couchbase_servers"]
    cbs_one_url = cluster_servers[0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_one_url)

    sg_db = "db"
    username = "autotest"
    password = "password"
    channels = ["TRANSACTIONS"]
    num_of_docs = 4
    doc_id = "transaction-sync-id"
    doc_ids = ""

    sg_client = MobileRestClient()
    doc_obj = Document(base_url)
    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    bucket = cb_server.get_bucket_names()[0]

    # disable replicas and rebalance the server
    cb_server.disable_replicas(bucket)
    cb_server.rebalance_server(cluster_servers)

    # randomly  generate replication ids
    for i in range(0, num_of_docs):
        doc_id = "txn_id_" + str(time.time())
        doc_ids = doc_id + "," + doc_ids
    # 1. Insert a transaction with 3 or more docs
    opt_doc_ids = doc_ids.replace("txn_id_", "insert-txn_id_")
    transactions_app_dir = "resources/data/transaction-performer.jar"
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channels)
    data = json.dumps(doc_body)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={} doccontent='{}'".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket, data)
    subprocess.check_output(cmd, shell=True)

    # 2. replication from server to SGW and to CBL"
    # 3. Verify all docs in transactions are pulled to CBL
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    _, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, continuous=True, replication_type="push_pull")
    replicator.wait_until_replicator_idle(repl)
    orig_cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(orig_cbl_doc_ids) == num_of_docs, "docs from committed transaction did not replicated to cbl"

    # 4. Replace the transaction with new content
    list_replace_ids = random.sample(orig_cbl_doc_ids, 2)
    replace_ids = ""
    for rep_id in list_replace_ids:
        replace_ids = rep_id + "," + replace_ids
    opt_doc_ids = replace_ids.replace("txn_id_", "replace-txn_id_")
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket)
    subprocess.check_output(cmd, shell=True)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    for id in list_replace_ids:
        cbl_doc = db.getDocument(cbl_db, id)
        doc_mut = doc_obj.toMutable(cbl_doc)
        doc_body1 = doc_obj.toMap(doc_mut)
        assert("_updated" in doc_body1["id"])
        assert("_updated" in doc_body1["content"])

    # 6. Delete the transaction
    # 7. Verify doc is removed in cbl
    list_deleted_ids = random.sample(orig_cbl_doc_ids, 2)
    delete_ids = ""
    for rep_id in list_deleted_ids:
        delete_ids = rep_id + "," + delete_ids
    opt_doc_ids = delete_ids.replace("txn_id_", "remove-txn_id_")
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket)
    subprocess.check_output(cmd, shell=True)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    for id in cbl_doc_ids:
        if id in list_deleted_ids:
            assert id not in cbl_doc_ids, "doc from transaction is not removed"
        else:
            assert id in cbl_doc_ids, "doc from transaction is removed though it is not removed from transaction"

    # 8. Rollback the transaction
    # 9. Verify rollback docs are not replicated to cbl
    doc_ids = ""
    for i in range(0, num_of_docs):
        doc_id = "txn_id_" + str(time.time())
        doc_ids = doc_id + "," + doc_ids
    opt_doc_ids = doc_ids.replace("txn_id_", "insert-txn_id_")
    opt_doc_ids = "{},rollback".format(opt_doc_ids)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={} doccontent='{}'".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket, data)
    subprocess.check_output(cmd, shell=True)
    cbl_doc_ids = db.getDocIds(cbl_db)
    rollback_ids = doc_ids.split(",")
    for id in rollback_ids:
        assert id not in cbl_doc_ids, "docs in rollback transaction is replicated to cbl"

    replicator.stop(repl)


@pytest.mark.transactions
@pytest.mark.syncgateway
@pytest.mark.cbl
def test_transactions_with_latest_updates(params_from_base_test_setup):
    '''
    @summary:
    1. Inserts a series of documents (A, B, C) in a transaction
    2. CBL is not syncing as yet. SGW does import
    3. Transaction updates (edits) a series of documents in this order  (A->A',B-> B',C-> C')  At the exact same time, CBL starts pulling docs via SGW.
    4. Replicate from SGW to CBL
    5. Verify CBL eventually pull all updated docs
    '''

    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    if not xattrs_enabled:
        pytest.skip('this test require --xattrs flag')
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cluster_servers = topology["couchbase_servers"]
    cbs_one_url = cluster_servers[0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_one_url)

    sg_db = "db"
    username = "autotest"
    password = "password"
    channels = ["TRANSACTIONS"]
    num_of_docs = 4
    doc_ids = ""

    sg_client = MobileRestClient()
    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    bucket = cb_server.get_bucket_names()[0]

    # disable replicas and rebalance the server
    cb_server.disable_replicas(bucket)
    cb_server.rebalance_server(cluster_servers)

    # randomly  generate replication ids
    for i in range(0, num_of_docs):
        doc_id = "txn_id_" + str(time.time())
        doc_ids = doc_id + "," + doc_ids
    opt_doc_ids = doc_ids.replace("txn_id_", "insert-txn_id_")
    # 1. Inserts a series of documents (A, B, C) in a transaction
    # 2. CBL is not syncing as yet. SGW does import
    transactions_app_dir = "resources/data/transaction-performer.jar"
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channels)
    data = json.dumps(doc_body)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={} doccontent='{}'".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket, data)
    subprocess.check_output(cmd, shell=True)

    # 3. Transaction updates (edits) a series of documents in this order  (A->A',B-> B',C-> C')  At the exact same time, CBL starts pulling docs via SGW.
    # replace_doc_body = document.create_doc(doc_id=doc_id, content="updated_doc", channels=channels, cbl=True)
    # replace_data = json.dumps(replace_doc_body)
    opt_doc_ids = doc_ids.replace("txn_id_", "replace-txn_id_")
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket)
    subprocess.check_output(cmd, shell=True)

    # 4. Replicate from SGW to CBL
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    _, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, continuous=True, replication_type="push_pull")
    replicator.wait_until_replicator_idle(repl)

    #  5. Verify CBL eventually should pull all updated docs only
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_docs:
        assert("_updated" in cbl_docs[doc]["id"])
        assert("_updated" in cbl_docs[doc]["content"])

    replicator.stop(repl)


@pytest.mark.transactions
@pytest.mark.syncgateway
@pytest.mark.cbl
def test_transactions_with_tombstoned_docs(params_from_base_test_setup):
    '''
    @summary:
    1. Insert a series of documents (A, B, C) in a transaction . CBL is not syncing as yet. SGW does import
    2. Update (edits) a series of documents in this order (A->A',B-> B' (tombstoned) ,C-> C') in a transaction At the exact same time, CBL starts pulling docs via SGW.
    3. CBL must eventually see A’. B’(tombstoned) and C’ (not in particular order)
    It is also possible that CBL sees any combination of A, A’,B, B’ (tombstoned) ,C,C’ before it eventually sees A’,B’ and C’ - It just depends on when the updates happen relative to when CBL is syncing.
    Note: Since SGW and CBL is not transaction aware and this is a distributed system, it is likely that CBL could be disconnected midway while syncing updates and could be in an inconsistent state. This is no different than how things work without transactions - it’s eventually consistent. Essentially we can never make transaction guarantees in a distributed system that operates under unreliable network conditions
    '''

    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    if not xattrs_enabled:
        pytest.skip('this test require --xattrs flag')
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cluster_servers = topology["couchbase_servers"]
    cbs_one_url = cluster_servers[0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_one_url)

    sg_db = "db"
    username = "autotest"
    password = "password"
    channels = ["TRANSACTIONS"]
    num_of_docs = 4
    doc_ids = ""

    sg_client = MobileRestClient()
    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    bucket = cb_server.get_bucket_names()[0]

    # disable replicas and rebalance the server
    cb_server.disable_replicas(bucket)
    cb_server.rebalance_server(cluster_servers)

    # randomly  generate replication ids
    for i in range(0, num_of_docs):
        doc_id = "txn_id_" + str(time.time())
        doc_ids = doc_id + "," + doc_ids
    opt_doc_ids = doc_ids.replace("txn_id_", "insert-txn_id_")
    removable_id = doc_ids.split(",")[1]
    # 1: Insert a series of documents (A, B, C) in a transaction . CBL is not syncing as yet. SGW does import
    # CBL is not syncing as yet. SGW does import
    transactions_app_dir = "resources/data/transaction-performer.jar"
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channels)
    data = json.dumps(doc_body)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={} doccontent='{}'".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket, data)
    subprocess.check_output(cmd, shell=True)

    # 2: Update (edits) a series of documents in this order (A->A',B-> B' (tombstoned) ,C-> C') in a transaction At the exact same time, CBL starts pulling docs via SGW.
    opt_doc_ids = doc_ids.replace("txn_id_", "replace-txn_id_")
    opt_doc_ids = opt_doc_ids.replace("replace-{}".format(removable_id), "remove-{}".format(removable_id))
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, opt_doc_ids, bucket)
    with ThreadPoolExecutor(max_workers=2) as tpe:
        shell_cmd_task = tpe.submit(shell_process, cmd)

        # 4. Replicate from SGW to CBL
        replicator = Replication(base_url)
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
        _, _, repl = replicator.create_session_configure_replicate(
            base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, continuous=True, replication_type="push_pull")
        replicator.wait_until_replicator_idle(repl)
        shell_cmd_task.result()

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    assert removable_id not in cbl_doc_ids, "tombstoned doc in transaction is not tombstoned in cbl"
    for doc in cbl_docs:
        assert "_updated" in cbl_docs[doc]["id"]
        assert "_updated" in cbl_docs[doc]["content"]
    replicator.stop(repl)


@pytest.mark.transactions
@pytest.mark.syncgateway
@pytest.mark.cbl
def test_transactions_with_simultaneous_doc_updates_docresurrection(params_from_base_test_setup):
    '''
    @summary:
    1: Insert a series of documents (A, B, C) in a transaction.
    2. Start replication from SGW to CBL.
    3. Updates (edits ) a series of documents in this order (A->A',B-> B',C-> C') in a transaction . At the exact same time, CBL also edits the same document B -> B”
    4. Indeterminate: The resulting state could be (A,B”,C) or (A’,B’,C’).It depends on when the B” comes in during transaction update ."
    5. Now have doc resurrect for document B
    '''

    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    if not xattrs_enabled:
        pytest.skip('this test require --xattrs flag')
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cluster_servers = topology["couchbase_servers"]
    cbs_one_url = cluster_servers[0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_one_url)

    sg_db = "db"
    username = "autotest"
    password = "password"
    channels = ["TRANSACTIONS"]
    num_of_docs = 4
    doc_ids = ""

    sg_client = MobileRestClient()
    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    bucket = cb_server.get_bucket_names()[0]

    # disable replicas and rebalance the server
    cb_server.disable_replicas(bucket)
    cb_server.rebalance_server(cluster_servers)

    # randomly  generate replication ids
    for i in range(0, num_of_docs):
        doc_id = "insert-txnId_" + str(time.time())
        doc_ids = doc_id + "," + doc_ids
    cbl_update_id = doc_ids.split(",")[1].split("-")[1]
    resurrect_doc_id = doc_ids.split(",")[2].split("-")[1]

    # 1: Insert a series of documents (A, B, C) in a transaction . CBL is not syncing as yet. SGW does import
    transactions_app_dir = "resources/data/transaction-performer.jar"
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channels)
    data = json.dumps(doc_body)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={} doccontent='{}'".format(transactions_app_dir, c.servers[0].host, doc_ids, bucket, data)
    subprocess.check_output(cmd, shell=True)

    # 2. Start replication from SGW to CBL.
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    _, _, repl = replicator.create_session_configure_replicate(
        base_url, sg_admin_url, sg_db, username, password, channels, sg_client, cbl_db, sg_blip_url, continuous=True, replication_type="push_pull")
    replicator.wait_until_replicator_idle(repl)

    # 3. Updates (edits ) a series of documents in this order (A->A',B-> B',C-> C') in a transaction . At the exact same time, CBL also edits the same document B -> B”
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    doc_ids = doc_ids.replace("insert-", "replace-")
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, doc_ids, bucket)
    with ThreadPoolExecutor(max_workers=2) as tpe:
        shell_cmd_task = tpe.submit(shell_process, cmd)
        for doc in cbl_db_docs:
            if cbl_db_docs[doc]["id"] == cbl_update_id:
                cbl_db_docs[doc]["content"] = "cbl_new_content"
        db.updateDocuments(cbl_db, cbl_db_docs)
        shell_cmd_task.result()

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_docs:
        if cbl_docs[doc]["id"] == cbl_update_id:
            assert("_updated" in cbl_docs[doc]["id"])
            assert("_updated" in cbl_docs[doc]["content"])

    # 4. Do doc resurrection of one of the doc in transaction and verify resureccted doc replicated to cbl
    resurrect_doc_ids = "remove-{}".format(resurrect_doc_id)
    resurrect_insert_doc_ids = "{},insert-{}".format(resurrect_doc_ids, resurrect_doc_id)
    cmd = "java -cp {} com.couchbase.transaction clusterip={} operationdocids={} bucket={}".format(transactions_app_dir, c.servers[0].host, resurrect_insert_doc_ids, bucket)
    subprocess.check_output(cmd, shell=True)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for doc in cbl_docs:
        if cbl_docs[doc]["id"] == resurrect_doc_id:
            assert("_updated" not in cbl_docs[doc]["id"])
            assert("_updated" not in cbl_docs[doc]["content"])
    replicator.stop(repl)


def shell_process(cmd):
    time.sleep(5)  # To make other process start before shell command executes
    subprocess.check_output(cmd, shell=True)
