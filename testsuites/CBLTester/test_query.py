import time
import pytest

from libraries.data.doc_generators import simple_user
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
from CBLClient.Replication import Replication
from keywords.utils import host_for_url
from libraries.testkit.cluster import Cluster
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery


def test_get_doc_ids(params_from_base_test_setup):
    """@summary
    Fectches all the doc ids
    Tests the below query
    let query = Query
                .select(SelectResult.expression(Expression.meta().id))
                .from(DataSource.database(database))
    """
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]

    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    db = Database(base_url)
    cbl_db = "test_db"
    sg_db = "db"
    sg_ip = host_for_url(sg_url)
    cbs_ip = host_for_url(cbs_url)
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Start and stop continuous replication
    replicator = Replication(base_url)
    log_info("Configuring replication")
    repl = replicator.configure_replication(source_db, target_url)
    log_info("Starting replication")
    replicator.start_replication(repl)
    # Wait for replication to complete
    time.sleep(60)

    log_info("Fecthing doc ids from the server")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where meta().id not like "_sync%"'.format(bucket_name)
    query = N1QLQuery(n1ql_query)
    doc_ids_from_n1ql = []
    for row in sdk_client.n1ql_query(query):
        doc_ids_from_n1ql.append(row["id"])

    log_info("Fecthing doc ids from CBL")
    ids_from_cbl = db.getDocIds(source_db)
    assert len(ids_from_cbl) == len(doc_ids_from_n1ql)
    assert sorted(ids_from_cbl) == sorted(doc_ids_from_n1ql)

    log_info("Stopping replication")
    replicator.stop_replication(repl)


def test_doc_get(params_from_base_test_setup):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.all())
                    .from(DataSource.database(database))
                    .where((Expression.meta().id).equalTo(doc_id))
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]

    sg_url = cluster_topology["sync_gateways"][0]["public"]
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    db = Database(base_url)
    cbl_db = "test_db"
    sg_db = "db"
    sg_ip = host_for_url(sg_url)
    cbs_ip = host_for_url(cbs_url)
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Start and stop continuous replication
    replicator = Replication(base_url)
    log_info("Configuring replication")
    repl = replicator.configure_replication(source_db, target_url)
    log_info("Starting replication")
    replicator.start_replication(repl)
    # Wait for replication to complete
    time.sleep(60)

    # Get doc from CBL through query
    doc_id = "airline_10"
    log_info("Fetching doc {} from CBL through query".format(doc_id))
    qy = Query(base_url)
    result_set = qy.query_get_doc(source_db, doc_id)
    doc_from_cbl = result_set[cbl_db]

    # Get doc from SDK through query
    log_info("Fetching doc {} from server through SDK".format(doc_id))
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    doc_from_server = sdk_client.get(doc_id).value

    assert doc_from_cbl == doc_from_server
    log_info("Stopping replication")
    replicator.stop_replication(repl)
