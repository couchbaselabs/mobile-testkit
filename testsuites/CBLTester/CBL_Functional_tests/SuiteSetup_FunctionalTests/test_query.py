import pytest

from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from operator import itemgetter
import numpy as np


def test_get_doc_ids(params_from_base_suite_setup):
    """@summary
    Fetches all the doc ids
    Tests the below query
    let query = Query
                .select(SelectResult.expression(Expression.meta().id))
                .from(DataSource.database(database))

    Verifies with n1ql - select meta().id from `bucket_name` where meta().id not like "_sync%"
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    db = Database(base_url)

    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching doc ids from the server")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where meta().id not like "_sync%" ORDER BY id'.format(bucket_name)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    doc_ids_from_n1ql = []
    for row in sdk_client.n1ql_query(query):
        doc_ids_from_n1ql.append(row["id"])

    log_info("Fetching doc ids from CBL")
    ids_from_cbl = db.getDocIds(source_db, limit=35000)

    assert len(ids_from_cbl) == len(doc_ids_from_n1ql)
    assert np.array_equal(sorted(ids_from_cbl), sorted(doc_ids_from_n1ql))
    log_info("Doc contents match between CBL and n1ql")


def test_any_operator(params_from_base_suite_setup):
    """@summary
    Fetches all the doc ids
    Tests the below query
    Query search_query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(whr_prop).equalTo(Expression.value(whr_val))
                        .and(ArrayExpression.any(dep_schedule).in(Expression.property(schedule))
                                .satisfies(departure_utc.greaterThan(Expression.value(departure_val)))));

    Verifies with n1ql - select meta().id from `{}` where type="route"
                        AND ANY departure IN schedule SATISFIES departure.utc > "23:41:00" END
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_url = cluster_topology['couchbase_servers'][0]

    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching doc ids from the server")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where type="route" ' \
                 'AND ANY departure IN schedule SATISFIES departure.utc > "23:41:00" END;'.format(bucket_name)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    doc_ids_from_n1ql = []
    for row in sdk_client.n1ql_query(query):
        doc_ids_from_n1ql.append(row["id"])

    # Fetching docs from CBL
    whr_prop = "type"
    whr_val = "route"
    schedule = "schedule"
    departure = "departure"
    departure_prop = "departure.utc"
    departure_val = "23:41:00"
    qy = Query(base_url)
    ids_from_cbl = qy.query_any_operator(source_db, schedule, departure, departure_prop,
                                         departure_val, whr_prop, whr_val)

    assert len(ids_from_cbl) == len(doc_ids_from_n1ql)
    assert np.array_equal(sorted(ids_from_cbl), sorted(doc_ids_from_n1ql))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("doc_id", [
    "airline_10",
    "doc_id_does_not_exist",
])
def test_doc_get(params_from_base_suite_setup, doc_id):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.all())
                    .from(DataSource.database(database))
                    .where((Expression.meta().id).equalTo(doc_id))

    Verifies with n1ql - select * from `bucket_name` where meta().id="doc_id"
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbl_db = params_from_base_suite_setup["suite_cbl_db"]
    enable_sample_bucket = "travel-sample"
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    log_info("Fetching doc {} from CBL through query".format(doc_id))
    qy = Query(base_url)
    result_set = qy.query_get_doc(source_db, doc_id)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result[cbl_db])

    # Get doc from n1ql through query
    log_info("Fetching doc {} from server through n1ql".format(doc_id))
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select * from `{}` where meta().id="{}" and meta().id not like "_sync%"'.format(bucket_name, doc_id)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        row[enable_sample_bucket].pop('_sync', None)
        docs_from_n1ql.append(row[enable_sample_bucket])

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('type')) == sorted(docs_from_n1ql, key=itemgetter('type'))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("limit, offset", [
    (5, 5),
    (-5, -5),
])
def test_get_docs_with_limit_offset(params_from_base_suite_setup, limit, offset):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
        .select(SelectResult.all())
        .from(DataSource.database(db))
        .limit(limit,offset: offset)

    Verifies with n1ql - select * from `travel-sample` where meta().id not like "_sync%" limit 5 offset 5
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_get_docs_limit_offset(source_db, limit, offset)
    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    if limit > 0:
        assert len(docs_from_cbl) == limit
        log_info("Found {} docs".format(limit))
    else:
        assert len(docs_from_cbl) == 0
        log_info("Found 0 docs")


@pytest.mark.parametrize("select_property1, select_property2, whr_key, whr_val", [
    ("name", "type", "country", "France"),
])
def test_multiple_selects(params_from_base_suite_setup, select_property1, select_property2, whr_key, whr_val):
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
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_multiple_selects(source_db, select_property1, select_property2, whr_key, whr_val)
    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select {}, {}, meta().id from `{}` where {}="{}"'.format(select_property1, select_property2, bucket_name, whr_key, whr_val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info(docs_from_n1ql)
    log_info(docs_from_cbl)
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4", [
    ("type", "hotel", "country", "United States", "country", "France", "vacancy", True),
])
def test_query_where_and_or(params_from_base_suite_setup, whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4):
    """ @summary
    Fetches docs with where an/or clause

    let searchQuery = Query
       .select(SelectResult.expression(Expression.meta().id))
       .from(DataSource.database(db))
       .where(Expression.property("type").equalTo("hotel")
           .and(Expression.property("country").equalTo("United States")
               .or(Expression.property("country").equalTo("France")))
               .and(Expression.property("vacancy").equalTo(true)))

    Verifies with n1ql - select meta().id from `travel-sample` t where t.type="hotel" and (t.country="United States" or t.country="France") and t.vacancy=true
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_where_and_or(source_db, whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4)
    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` t where t.{}="{}" and (t.{}="{}" or t.{}="{}") and t.{}={}'.format(bucket_name, whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key, whr_val, select_property1, select_property2, like_key, like_val", [
    ("type", "landmark", "country", "name", "name", "Royal Engineers Museum"),
    ("type", "landmark", "country", "name", "name", "Royal engineers museum"),
    ("type", "landmark", "country", "name", "name", "eng%e%"),
    ("type", "landmark", "country", "name", "name", "Eng%e%"),
    ("type", "landmark", "country", "name", "name", "%eng____r%"),
    ("type", "landmark", "country", "name", "name", "%Eng____r%"),
])
def test_query_pattern_like(params_from_base_suite_setup, whr_key, whr_val, select_property1, select_property2, like_key, like_val):
    """ @summary
    Fetches docs with like clause

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("country")),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("landmark")
            .and(Expression.property("name").like("Royal Engineers Museum")))

    Verifies with n1ql - select meta().id, country, name from `travel-sample` t where t.type="landmark"  and t.name like "Royal Engineers Museum"
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_like(source_db, whr_key, whr_val, select_property1, select_property2, like_key, like_val)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {}, {} from `{}` t where t.{}="{}"  and t.{} like "{}"'.format(select_property1, select_property2, bucket_name, whr_key, whr_val, like_key, like_val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key, whr_val, select_property1, select_property2, regex_key, regex_val", [
    ("type", "landmark", "country", "name", "name", '\\bEng.*e\\b'),
    ("type", "landmark", "country", "name", "name", "\\beng.*e\\b"),
])
def test_query_pattern_regex(params_from_base_suite_setup, whr_key, whr_val, select_property1, select_property2, regex_key, regex_val):
    """ @summary
    Fetches docs with like clause

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("country")),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("landmark")
            .and(Expression.property("name").regex("\\bEng.*e\\b")))

    Verifies with n1ql - select meta().id, country, name from `travel-sample` t where t.type="landmark" and REGEXP_CONTAINS(t.name, "\\bEng.*e\\b")
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    log_info("regex_val: {}".format(regex_val))
    result_set = qy.query_regex(source_db, whr_key, whr_val, select_property1, select_property2, regex_key, regex_val)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

    # \ has to be escaped for n1ql
    regex_val_n1ql = regex_val.replace('\\b', '\\\\b')
    n1ql_query = 'select meta().id, {}, {} from `{}` t where t.{}="{}" and REGEXP_CONTAINS(t.{}, \'{}\')'.format(select_property1, select_property2, bucket_name, whr_key, whr_val, regex_key, regex_val_n1ql)
    log_info("n1ql_query: {}".format(n1ql_query))
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, limit", [
    ("name", 100),
])
def test_query_isNullOrMissing(params_from_base_suite_setup, select_property1, limit):
    """ @summary
    Fetches docs with where email is null or missing

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("email").isNullOrMissing())

    Verifies with n1ql - select meta().id from `travel-sample` t where meta().id not like "_sync%" and (t.name IS NULL or t.name IS MISSING)
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_isNullOrMissing(source_db, select_property1, limit)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {} from `{}` t where meta().id not like "_sync%" and (t.{} IS NULL or t.{} IS MISSING) order by "{}" asc limit {}'.format(select_property1, bucket_name, select_property1, select_property1, select_property1, limit)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info(docs_from_n1ql)
    log_info(docs_from_cbl)
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, whr_key, whr_val", [
    ("title", "type", "hotel"),
])
def test_query_ordering(params_from_base_suite_setup, select_property1, whr_key, whr_val):
    """ @summary
    Fetches docs in ascending order

      let searchQuery = Query
        .select(
            SelectResult.expression(Expression.meta().id),
            SelectResult.expression(Expression.property("title")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("hotel"))
        .orderBy(Ordering.property("title").ascending())

    Verifies with n1ql - select meta().id, title from `travel-sample` t where t.type = "hotel" order by "title" asc
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_ordering(source_db, select_property1, whr_key, whr_val)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {} from `{}` t where t.{} = "{}" order by "{}" asc'.format(select_property1, bucket_name, whr_key, whr_val, select_property1)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, select_property2, substring", [
    ("email", "name", "gmail.com"),
])
def test_query_substring(params_from_base_suite_setup, select_property1, select_property2, substring):
    """ @summary
    Fetches docs in with a matching substring

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("email")),
                SelectResult.expression(Function.upper(Expression.property("name"))))
        .from(DataSource.database(db))
        .where(Expression.property("email").and(Function.contains(Expression.property("email"),
                 substring: "gmail.com")))

    Verifies with n1ql - select meta().id, email, UPPER(name) from `travel-sample` t where CONTAINS(t.email, "gmail.com")
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_substring(source_db, select_property1, select_property2, substring)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    log_info("docs_from_cbl: {}".format(docs_from_cbl))

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {}, UPPER({}) from `{}` t where CONTAINS(t.{}, "{}")'.format(select_property1, select_property2, bucket_name, select_property1, substring)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    for doc in docs_from_cbl:
        assert doc in docs_from_n1ql
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to", [
    ("name", "type", "hotel", "country", "France", "Le Clos Fleuri"),
])
def test_query_collation(params_from_base_suite_setup, select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to):
    """ @summary
    Fetches docs using collation
      let collator = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true)

     let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("hotel")
            .and(Expression.property("country").equalTo("France"))
            .and(Expression.property("name").collate(collator).equalTo("Le Clos Fleuri")))

    Verifies with n1ql - select meta().id, name from `travel-sample` t where t.type="hotel" and t.country = "France" and lower(t.name) = lower("Le Clos Fleuri")
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_collation(source_db, select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {} from `{}` t where t.{}="{}" and t.{} = "{}" and lower(t.{}) = lower("{}")'.format(select_property1, bucket_name, whr_key1, whr_val1, whr_key2, whr_val2, select_property1, equal_to)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, select_property2, select_property3, select_property4, select_property5, whr_key1, whr_key2, whr_key3, whr_val1, whr_val2, whr_val3, join_key", [
    ("name", "callsign", "destinationairport", "stops", "airline", "type", "type", "sourceairport", "route", "airline", "SFO", "airlineid"),
])
def test_query_join(params_from_base_suite_setup, select_property1,
                    select_property2, select_property3, select_property4,
                    select_property5, whr_key1, whr_key2, whr_key3,
                    whr_val1, whr_val2, whr_val3, join_key):
    """ @summary
    Query query = QueryBuilder
                .selectDistinct(
                        SelectResult.expression(Expression.property(prop1).from(main)),
                        SelectResult.expression(Expression.property(prop2).from(main)),
                        SelectResult.expression(Expression.property(prop3).from(secondary)),
                        SelectResult.expression(Expression.property(prop4).from(secondary)),
                        SelectResult.expression(Expression.property(prop5).from(secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.join(DataSource.database(db).as(secondary))
                    .on(Expression.property(joinKey)))
                .where(Expression.property(whrKey1).from(main).equalTo(whrVal1)
                    .and(Expression.property(whrKey2).from(main).equalTo(whrVal2))
                    .and(Expression.property(whrKey3).from(main).equalTo(whrVal3)))
                .limit(limit);)

    Verifies with n1ql -
    SELECT DISTINCT airline.name, airline.callsign, route.destinationairport, route.stops, route.airline
    FROM `travel-sample` route
      JOIN `travel-sample` airline
      ON KEYS route.airlineid
    WHERE route.type = "route"
      AND airline.type = "airline"
      AND route.sourceairport = "SFO"
    LIMIT 2;
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_join(source_db, select_property1,
                               select_property2, select_property3,
                               select_property4, select_property5,
                               whr_key1, whr_key2, whr_key3, whr_val1,
                               whr_val2, whr_val3, join_key)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select distinct airline.{}, airline.{}, route.{}, '\
        'route.{}, route.{} from `{}` route join `{}` airline '\
        'on keys route.{} where route.{}="{}" and '\
        'airline.{} = "{}" and route.{} = "{}"'.format(
            select_property1, select_property2,
            select_property3, select_property4,
            select_property5, bucket_name, bucket_name,
            join_key, whr_key1, whr_val1, whr_key2, whr_val2,
            whr_key3, whr_val3)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    t = [i for i in docs_from_cbl if i not in docs_from_n1ql] + [j for j in docs_from_n1ql if j not in docs_from_cbl]
    assert len(t) == 0
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, select_property2, select_property3, whr_key1, whr_key2, whr_val1, whr_val2, join_key1, join_key2, limit", [
    ("airline", "sourceairport", "country", "country", "stops", "United States", 0, "icao", "destinationairport", 10),
])
def test_query_inner_join(params_from_base_suite_setup, select_property1,
                          select_property2, select_property3, whr_key1, whr_key2,
                          whr_val1, whr_val2, join_key1, join_key2, limit):
    """ @summary
    Query query = QueryBuilder
                .select(SelectResult.expression(Expression.property(prop1).from(main)),
                        SelectResult.expression(Expression.property(prop2).from(main)),
                        SelectResult.expression(Expression.property(prop3).from(secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.innerJoin(DataSource.database(db).as(secondary))
                        .on(Expression.property(joinKey1).from(main).equalTo(Expression.property(joinKey2).from(secondary))
                                .and(Expression.property(whrKey1).from(main).equalTo(Expression.string(whrVal1)))
                                .and(Expression.property(whrKey2).from(secondary).equalTo(Expression.string(whrVal2)))));

    Verifies with n1ql -
    SELECT
      route.airline,
      route.sourceairport,
      airport.country
    FROM
      `travel-sample` route
      INNER JOIN `travel-sample` airport ON airport.icao = route.destinationairport
    WHERE
      airport.country = "United States"
      AND route.stops = 0
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_inner_join(source_db, select_property1,
                                     select_property2, select_property3, whr_key1,
                                     whr_key2, whr_val1, whr_val2,
                                     join_key1, join_key2, limit)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    n1ql_query = 'select  route.{}, route.{}, airport.{} '\
        'from `{}` route inner join `{}` airport '\
        'on airport.{} = route.{} where airport.{}="{}" and '\
        'route.{} = {} order by route.{} asc limit {}'.format(
            select_property1, select_property2,
            select_property3, bucket_name, bucket_name,
            join_key1, join_key2, whr_key1, whr_val1, whr_key2, whr_val2,
            select_property1, limit)
    log_info(n1ql_query)

    assert len(docs_from_cbl) == limit
    log_info("Found {} docs".format(len(docs_from_cbl)))


@pytest.mark.parametrize("select_property1, select_property2, whr_key1, whr_key2, whr_val1, whr_val2, limit", [
    ("country", "city", "type", "type", "airport", "airline", 10),
])
def test_query_cross_join(params_from_base_suite_setup, select_property1,
                          select_property2, whr_key1, whr_key2,
                          whr_val1, whr_val2, limit):
    """ @summary
    Query query = QueryBuilder
                .select(SelectResult.expression(Expression.property(prop1).from(main)).as(firstName),
                        SelectResult.expression(Expression.property(prop1).from(secondary)).as(secondName),
                        SelectResult.expression(Expression.property(prop2).from(secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.crossJoin(DataSource.database(db).as(secondary)))
                .where(Expression.property(whrKey1).from(main).equalTo(Expression.string(whrVal1))
                        .and(Expression.property(whrKey2).from(main).equalTo(Expression.string(whrVal2))));
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_cross_join(source_db, select_property1,
                                     select_property2, whr_key1,
                                     whr_key2, whr_val1, whr_val2, limit)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    assert len(docs_from_cbl) == limit
    log_info("Found {} docs".format(len(docs_from_cbl)))


@pytest.mark.parametrize("select_property, limit", [
    ("airlineid", 10),
])
def test_query_left_join(params_from_base_suite_setup, select_property, limit):
    """ @summary
    Fetches docs using collation
      let collator = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true)

     let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("hotel")
            .and(Expression.property("country").equalTo("France"))
            .and(Expression.property("name").collate(collator).equalTo("Le Clos Fleuri")))

    Verifies with n1ql - SELECT airline.*, route.* FROM `travel-sample` route LEFT JOIN `travel-sample` airline ON KEYS route.airlineid
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_left_join(source_db, select_property, limit)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    n1ql_query = 'select airline.*, route.* from `{}` route LEFT JOIN `{}` route ON KEYS route.{} order by route.{} limit {}'.format(bucket_name, bucket_name, select_property, select_property, limit)
    log_info(n1ql_query)

    assert len(docs_from_cbl) == limit
    log_info("Found {} docs".format(len(docs_from_cbl)))


@pytest.mark.parametrize("select_property, limit", [
    ("airlineid", 10),
])
def test_query_left_outer_join(params_from_base_suite_setup, select_property, limit):
    """ @summary
    Fetches docs using collation
      let collator = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true)

     let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("type").equalTo("hotel")
            .and(Expression.property("country").equalTo("France"))
            .and(Expression.property("name").collate(collator).equalTo("Le Clos Fleuri")))

    Verifies with n1ql - SELECT airline.*, route.* FROM `travel-sample` route LEFT OUTER JOIN `travel-sample` airline ON KEYS route.airlineid
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    log_info("Fetching docs from CBL through query")
    qy = Query(base_url)
    result_set = qy.query_left_join(source_db, select_property, limit)

    docs_from_cbl = []

    for docs in result_set:
        docs_from_cbl.append(docs)

    # Get doc from n1ql through query
    log_info("Fetching docs from server through n1ql")
    bucket_name = "travel-sample"
    n1ql_query = 'select airline.*, route.* from `{}` route LEFT OUTER JOIN `{}` route ON KEYS route.{} order by route.{} limit {}'.format(bucket_name, bucket_name, select_property, select_property, limit)
    log_info(n1ql_query)

    assert len(docs_from_cbl) == limit
    log_info("Found {} docs".format(len(docs_from_cbl)))


@pytest.mark.parametrize("prop, val", [
    ("country", "France"),
    ("type", "airline")
])
def test_equal_to(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).equalTo(val));

    Verifies with n1ql - select meta().id from `bucket_name` where country = "france"
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_equal_to(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} = "{}" order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val", [
    ("country", "United States"),
    ("type", "airline")
])
def test_not_equal_to(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).notEqualTo(val));

    Verifies with n1ql - select meta().id from `bucket_name` where country != "France"
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_not_equal_to(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} != "{}" order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val", [
    ("id", 1000),
])
def test_greater_than(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).greaterThan(val));

    Verifies with n1ql - select meta().id from `bucket_name` where id > 1000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_greater_than(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} > {} and meta().id not like "_sync%" order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val", [
    ("id", 1000),
])
def test_greater_than_or_equal_to(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).greaterThanOrEqualTo(val));

    Verifies with n1ql - select meta().id from `bucket_name` where id >= 1000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_greater_than_or_equal_to(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} >= {} and meta().id not like "_sync%" order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val", [
    ("id", 1000),
])
def test_less_than(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).lessThan(val));

    Verifies with n1ql - select meta().id from `bucket_name` where id < 1000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_less_than(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} < {} order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val", [
    ("id", 1000),
])
def test_less_than_or_equal_to(params_from_base_suite_setup, prop, val):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).lessThanOrEqualTo(val));

    Verifies with n1ql - select meta().id from `bucket_name` where id <= 1000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_less_than_or_equal_to(source_db, prop, val)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} <= {} order by meta().id asc'.format(bucket_name, prop, val)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val1, val2", [
    ("country", "France", "United States"),
])
def test_in(params_from_base_suite_setup, prop, val1, val2):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).in(Expression.value(valueList)));

    Verifies with n1ql - select meta().id from `bucket_name` where country in ['France', 'United States']
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_in(source_db, prop, val1, val2)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} in ["{}", "{}"] order by meta().id asc'.format(bucket_name, prop, val1, val2)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val1, val2", [
    ("id", 1000, 2000),
])
def test_between(params_from_base_suite_setup, prop, val1, val2):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).between(val1, val2));

    Verifies with n1ql - select meta().id from `bucket_name` where id between 1000 and 2000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_between(source_db, prop, val1, val2)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} between {} and {} order by meta().id asc'.format(bucket_name, prop, val1, val2)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop", [
    "callsign",
    "iata"
])
def test_is(params_from_base_suite_setup, prop):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).is(Expression.value(null)));

    Verifies with n1ql - select meta().id from `bucket_name` where iata is null
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_is(source_db, prop)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} is null order by meta().id asc'.format(bucket_name, prop)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop", [
    "callsign",
    "iata"
])
def test_isnot(params_from_base_suite_setup, prop):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).isNot(Expression.value(null)));

    Verifies with n1ql - select meta().id from `bucket_name` where iata is not null
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_isNot(source_db, prop)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id, {} from `{}` where {} is not null order by meta().id asc'.format(prop, bucket_name, prop)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl, key=itemgetter('id')) == sorted(docs_from_n1ql, key=itemgetter('id'))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val1, val2", [
    ("id", 1000, 2000),
])
def test_not(params_from_base_suite_setup, prop, val1, val2):
    """ @summary
    Fetches a doc
    Tests the below query
    Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.not(Expression.property(prop).between(val1, val2)));

    Verifies with n1ql - select meta().id from `bucket_name` where id not between 1000 and 2000
    """
    cluster_topology = params_from_base_suite_setup["cluster_topology"]
    source_db = params_from_base_suite_setup["suite_source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_suite_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    qy = Query(base_url)
    result_set = qy.query_not(source_db, prop, val1, val2)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where {} not between {} and {} and meta().id not like "_sync%" order by meta().id asc'.format(bucket_name, prop, val1, val2)
    log_info(n1ql_query)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert np.array_equal(sorted(docs_from_cbl, key=itemgetter('id')), sorted(docs_from_n1ql, key=itemgetter('id')))
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("prop, val, doc_type, stemming", [
    # With Stemming
    ("content", "beautifully", "landmark", True),
    ("content", "cons*", "landmark", True),  # Wildcard Expression/ Prefix expression
    ("content", "of the beautiful", "landmark", True),  # Search with stop words
    ("content", "local beautiful", "landmark", True),  # Search ignoring stop words
    ("content", "'\"foods including'\"", "landmark", True),  # phrase queries
    ("content", "'beautiful NEAR/7 \"local\"'", "landmark", True),  # near queries
    # Without Stemming
    ("content", "beautiful", "landmark", False),
    ("content", "cons*", "landmark", False),  # Wildcard Expression/ Prefix expression
    ("content", "of the beautiful", "landmark", False),  # Search with stop words
    ("content", "local beautiful", "landmark", False),  # Search ignoring stop words
    ("content", "'\"foods including'\"", "landmark", False),  # phrase queries
    ("content", "'beautiful NEAR/7 \"local\"'", "landmark", False),  # near queries
])
def test_single_property_fts(params_from_base_suite_setup, prop, val, doc_type, stemming):
    """ @summary
    Fetches a doc
    Tests the below query
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    # Get doc from CBL through query
    qy = Query(base_url)
    limit = 10

    result_set = qy.query_single_property_fts(source_db, prop, val,
                                              doc_type, limit, stemming)

    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            log_info("In the for ")
            docs_from_cbl.append(result)
            log_info(result)
    assert 0 < len(docs_from_cbl) <= limit


@pytest.mark.parametrize("prop1, prop2, val, doc_type, stemming", [
    # with stemming
    ("content", "name", "centre art", "landmark", True),
    ("content", "name", "tow*", "landmark", True),  # wild cards
    ("content", "name", "^Beautiful", "landmark", True),  # checking for content at the start
    ("content", "name", "name:cafe art", "landmark", True),  # overriding the property to be indexed
    ("content", "name", "beautiful OR arts", "landmark", True),  # OR logical expression
    ("content", "name", "beauty AND art", "landmark", True),  # AND logical expression
    ("content", "name", "(beauty AND art) OR cafe", "landmark", True),  # mix logical expression !!!!Alert
    ("content", "name", "(beautiful OR art) AND photograph", "landmark", True),  # mix logical expression
    ("content", "name", "restaurant NOT chips", "landmark", True),  # NOT logical expression
    # Without stemming
    ("content", "name", "centre art", "landmark", False),
    ("content", "name", "town*", "landmark", True),  # wild card
    ("content", "name", "^Beautiful", "landmark", False),  # checking for content at the start
    ("content", "name", "name:cafe art", "landmark", False),  # overriding the property to be indexed
    ("content", "name", "beautiful OR arts", "landmark", False),  # OR logical expression
    ("content", "name", "beautiful AND art", "landmark", False),  # AND logical expression
    ("content", "name", "(beauty AND splendour) OR food", "landmark", False),  # mix logical expression
    ("content", "name", "restaurant NOT chips", "landmark", False),  # NOT logical expression
])
def test_multiple_property_fts(params_from_base_suite_setup, prop1, prop2, val, doc_type, stemming):
    """ @summary
    Fetches a doc
    Tests the below query
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    # Get doc from CBL through query
    qy = Query(base_url)
    limit = 10
    result_set = qy.query_multiple_property_fts(source_db, prop1, prop2,
                                                val, doc_type, limit,
                                                stemming)
    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)
            log_info(result)
    assert 0 < len(docs_from_cbl) <= limit


@pytest.mark.parametrize("prop, val, doc_type", [
    ("content", "beautiful", "landmark"),
])
def test_fts_with_ranking(params_from_base_suite_setup, prop, val, doc_type):
    """ @summary
    Fetches a doc
    Tests the below query
    """
    source_db = params_from_base_suite_setup["suite_source_db"]
    base_url = params_from_base_suite_setup["base_url"]

    # Get doc from CBL through query
    qy = Query(base_url)
    limit = 10
    result_set = qy.query_fts_with_ranking(source_db, prop, val,
                                           doc_type, limit)
    docs_from_cbl = []
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)
            log_info(result)
    assert 0 < len(docs_from_cbl) <= limit


@pytest.mark.parametrize("doc_id_prefix", [
    ("doc_with_double_1")
])
def test_getDoc_withValueTypeDouble(params_from_base_suite_setup, doc_id_prefix):
    """ @summary
    1. Create docs with one of the column having double value
    2. Fetch the doc using where value as double value
    Fetches a doc
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.expression(Meta.id),
                SelectResult.expression(Expression.property(item)),
                SelectResult.expression(Expression.property(item_price)))
            .from(DataSource.database(database))
            .where(Expression.property(item_price).equalTo(2.754));

    """
    base_url = params_from_base_suite_setup["base_url"]
    database = Database(base_url)
    db_name = "db_name"

    # Create docs with double and retrieve
    doc_id_prefix = doc_id_prefix
    num_of_docs = 5
    db = database.create(db_name)
    documents = dict()
    ids = []
    for i in range(num_of_docs):
        data = {}
        doc_id = "{}_{}".format(doc_id_prefix, i)
        ids.append(doc_id)
        data["item"] = i
        data["item_price"] = i + 0.754
        documents[doc_id] = data
    database.saveDocuments(db, documents)
    qy = Query(base_url)

    # Query cblite database with key value type 'double'
    select_property1 = "item"
    select_property2 = "item_price"
    whr_key = "item_price"
    whr_val = 2.754
    result_set = qy.query_multiple_selects_forDoubleValue(db, select_property1, select_property2, whr_key, whr_val)
    docs_from_cbl = []
    for docs in result_set:
        docs_from_cbl.append(docs)
    assert len(docs_from_cbl) == 1, "did not get the write result after querying with float value"


@pytest.mark.parametrize("doc_id_prefix", [
    ("doc_with_double_1")
])
def test_getDoc_withLocale(params_from_base_suite_setup, doc_id_prefix):
    """ @summary
    1. Add docs with locale name having '-'
    2. Fetch the doc
    3.
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.expression(Meta.id),
                    SelectResult.expression(Expression.property(select_property1)),
                    SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .orderBy(Ordering.expression(locale_key.collate(with_locale_value)))

    """
    base_url = params_from_base_suite_setup["base_url"]
    database = Database(base_url)
    qy = Query(base_url)

    # Create docs with double and retrieve
    num_of_docs = 5
    db = database.create("db_name")
    documents = dict()
    ids = []
    for i in range(num_of_docs):
        data = {}
        doc_id = "{}_{}".format(doc_id_prefix, i)
        ids.append(doc_id)
        data["locale"] = "ko-Kore_US"
        data["credit"] = "credict-{}".format(i + 10)
        documents[doc_id] = data
    database.saveDocuments(db, documents)

    select_property1 = "locale"
    select_property2 = "credit"
    whr_key = "locale"
    locale = "ko-Kore_US"
    result_set = qy.query_multiple_selects_OrderByLocaleValue(db, select_property1, select_property2, whr_key, locale)
    docs_from_cbl = []
    for docs in result_set:
        docs_from_cbl.append(docs)
    assert len(docs_from_cbl) == 5, "Results for locale with - did not return 5 records"


@pytest.mark.parametrize("doc_id_prefix", [
    ("doc_with_no_data_1")
])
def test_getDoc_withNoData(params_from_base_suite_setup, doc_id_prefix):
    """ @summary
    1. Add a doc with doc_id = Meta.id and data = empty dictionary
    2. Fetch the doc
    3.run the below query
        Query query = QueryBuilder
            .select(SelectResult.all())
            .from(DataSource.database(database))
            .where((Meta.id).equalTo(doc_id));
    """
    base_url = params_from_base_suite_setup["base_url"]
    database = Database(base_url)
    qy = Query(base_url)

    # Create docs with empty data
    db = database.create("db_name")
    documents = dict()

    data = {}
    doc_id = "{}_{}".format(doc_id_prefix, 0)
    documents[doc_id] = data
    database.saveDocuments(db, documents)

    result_set = qy.query_get_doc(db, doc_id)
    docs_from_cbl = []
    for docs in result_set:
        docs_from_cbl.append(docs)
    assert len(docs_from_cbl) == 1, "Results for doc with empty data - did not return the record"


def test_query_arthimetic(params_from_base_suite_setup):
    """
        @summary:
        1. Query on arthimetic call
        2. Verify no crash happens

    """

    cbl_db = params_from_base_suite_setup["suite_source_db"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    base_url = params_from_base_suite_setup["base_url"]

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')

    qy = Query(base_url)
    qy.query_arthimetic(cbl_db)


def test_live_query_response_delay_time(params_from_base_suite_setup):
    """
    note: this test case is for android/java only
    1. call /query_getLiveQueryResponseTime to get delay timer
    2. validate delay timer is less than 200 millisecond
    """
    base_url = params_from_base_suite_setup["base_url"]
    db = params_from_base_suite_setup["suite_db"]
    cbl_db = params_from_base_suite_setup["suite_source_db"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]

    if liteserv_platform in ["ios", "net-msft", "net-uwp", "xamarin-ios", "xamarin-android"]:
        pytest.skip('This test case is for android/java only')

    channels = ["live-query"]
    num_of_docs = 100
    db.create_bulk_docs(num_of_docs, "live-query-doc", db=cbl_db, channels=channels)

    doc_ids = db.getDocIds(cbl_db)
    docs = db.getDocuments(cbl_db, doc_ids)
    seq_num = 1
    for doc_id, doc_body in docs.items():
        if "live-query-doc" in doc_id:
            doc_body["sequence_number"] = seq_num
            db.updateDocument(database=cbl_db, data=doc_body, doc_id=doc_id)
            seq_num += 1

    qy = Query(base_url)
    delay_timer = qy.query_get_live_query_delay_time(cbl_db)
    log_info("delay_timer is counted as {}".format(delay_timer))
    assert delay_timer < 200, "delay timer cannot be longer than 200 millionsec"
