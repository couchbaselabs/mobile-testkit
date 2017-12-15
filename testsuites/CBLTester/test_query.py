import time
import pytest

from libraries.data.doc_generators import simple_user
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
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

    Verifies with n1ql - select meta().id from `bucket_name` where meta().id not like "_sync%"
    """
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbl_db = params_from_base_test_setup["cbl_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    db = Database(base_url)
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching doc ids from the server")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where meta().id not like "_sync%"'.format(bucket_name)
    query = N1QLQuery(n1ql_query)
    doc_ids_from_n1ql = []
    for row in sdk_client.n1ql_query(query):
        doc_ids_from_n1ql.append(row["id"])

    log_info("Fetching doc ids from CBL")
    ids_from_cbl = db.getDocIds(source_db)
    assert len(ids_from_cbl) == len(doc_ids_from_n1ql)
    assert sorted(ids_from_cbl) == sorted(doc_ids_from_n1ql)


def test_doc_get(params_from_base_test_setup):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.all())
                    .from(DataSource.database(database))
                    .where((Expression.meta().id).equalTo(doc_id))

    Verifies with n1ql - select * from `bucket_name` where meta().id="doc_id"
    """
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbl_db = params_from_base_test_setup["cbl_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    doc_id = "airline_10"
    log_info("Fetching doc {} from CBL through query".format(doc_id))
    qy = Query(base_url)
    result_set = qy.query_get_doc(source_db, doc_id)
    doc_from_cbl = result_set[cbl_db]
    log_info("doc_from_cbl: {}".format(doc_from_cbl))

    # doc_from_getdoc = qy.query_get_doc(source_db, doc_id)
    # doc_from_cbl = result_set[cbl_db]
    # log_info("doc_from_cbl: {}".format(doc_from_cbl))

    # Get doc from n1ql through query
    log_info("Fetching doc {} from server through n1ql".format(doc_id))
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select * from `{}` where meta().id="{}"'.format(bucket_name, doc_id)
    query = N1QLQuery(n1ql_query)
    doc_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        doc_from_n1ql = row[bucket_name]

    assert doc_from_cbl == doc_from_n1ql


def test_get_docs_with_limit_offset(params_from_base_test_setup):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
        .select(SelectResult.all())
        .from(DataSource.database(db))
        .limit(limit,offset: offset)

    Verifies with n1ql - select * from `travel-sample` where meta().id not like "_sync%" limit 5 offset 5
    """
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbl_db = params_from_base_test_setup["cbl_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    limit = 5
    offset = 5
    result_set = qy.query_get_docs_limit_offset(source_db, limit, offset)
    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs[cbl_db])

    assert len(docs_from_cbl) == limit

    for i in docs_from_cbl:
        log_info("doc: {}".format(i))

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select * from `{}` where meta().id  not like "_sync%" limit {} offset {}'.format(bucket_name, limit, offset)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row[bucket_name])

    # TODO compare docs
    # null gets returned as <null>
    assert len(docs_from_cbl) == len(docs_from_n1ql)


def test_multiple_selects(params_from_base_test_setup):
    """ @summary
    Fetches multiple fields

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property(select_property1)),
                SelectResult.expression(Expression.property(select_property2)))
        .from(DataSource.database(database))
        .where((Expression.property(whr_key)).equalTo(whr_val))

    Verifies with n1ql - select name, type, meta().id from `travel-sample` where country="France"
    """
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbl_db = params_from_base_test_setup["cbl_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    select_property1 = "name"
    select_property2 = "type"
    whr_key = "country"
    whr_val = "France"
    result_set = qy.query_multiple_selects(source_db, select_property1, select_property2, whr_key, whr_val)
    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    log_info("docs_from_cbl: {}".format(docs_from_cbl))

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select {}, {}, meta().id from `{}` where {}="{}"'.format(select_property1, select_property2, bucket_name, whr_key, whr_val)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    # TODO compare docs
    # null gets returned as <null>

    assert len(docs_from_cbl) == len(docs_from_n1ql)
