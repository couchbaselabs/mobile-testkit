import pytest

from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery


def test_get_doc_ids(params_from_base_test_setup):
    """@summary
    Fetches all the doc ids
    Tests the below query
    let query = Query
                .select(SelectResult.expression(Expression.meta().id))
                .from(DataSource.database(database))

    Verifies with n1ql - select meta().id from `bucket_name` where meta().id not like "_sync%"
    """
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    base_url = params_from_base_test_setup["base_url"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    db = Database(base_url)

    cbs_ip = host_for_url(cbs_url)

    log_info("Fetching doc ids from the server")
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select meta().id from `{}` where meta().id not like "_sync%" ORDER BY id'.format(bucket_name)
    query = N1QLQuery(n1ql_query)
    doc_ids_from_n1ql = []
    for row in sdk_client.n1ql_query(query):
        doc_ids_from_n1ql.append(row["id"])
   
    log_info("Fetching doc ids from CBL")
    ids_from_cbl = db.getDocIds(source_db)

    assert len(ids_from_cbl) == len(doc_ids_from_n1ql)
    assert sorted(ids_from_cbl) == sorted(doc_ids_from_n1ql)
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("doc_id", [
    ("airline_10"),
    # ("doc_id_does_not_exist"),
])
def test_doc_get(params_from_base_test_setup, doc_id):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
                    .select(SelectResult.all())
                    .from(DataSource.database(database))
                    .where((Expression.meta().id).equalTo(doc_id))

    Verifies with n1ql - select * from `bucket_name` where meta().id="doc_id"
    """
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
    cbs_ip = host_for_url(cbs_url)

    # Get doc from CBL through query
    log_info("Fetching doc {} from CBL through query".format(doc_id))
    qy = Query(base_url)
    result_set = qy.query_get_doc(source_db, doc_id)

    docs_from_cbl = []
    print "result set of clb is ", result_set
    if result_set != -1 and result_set is not None:
        for result in result_set:
            docs_from_cbl.append(result)

    # Get doc from n1ql through query
    log_info("Fetching doc {} from server through n1ql".format(doc_id))
    bucket_name = "travel-sample"
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')
    n1ql_query = 'select * from `{}` where meta().id="{}"'.format(bucket_name, doc_id)
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row[bucket_name])

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    print "cbl docs - ", docs_from_cbl
    print "docs from n1ql0---  ", docs_from_n1ql
    assert docs_from_cbl == docs_from_n1ql
    log_info("Doc contents match between CBL and n1ql")


@pytest.mark.parametrize("limit, offset", [
    (5, 5),
    (-5, -5),
])
def test_get_docs_with_limit_offset(params_from_base_test_setup, limit, offset):
    """ @summary
    Fetches a doc
    Tests the below query
    let searchQuery = Query
        .select(SelectResult.all())
        .from(DataSource.database(db))
        .limit(limit,offset: offset)

    Verifies with n1ql - select * from `travel-sample` where meta().id not like "_sync%" limit 5 offset 5
    """
    source_db = params_from_base_test_setup["source_db"]
    base_url = params_from_base_test_setup["base_url"]

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
def test_multiple_selects(params_from_base_test_setup, select_property1, select_property2, whr_key, whr_val):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    # log_info("Found cbl docs {} docs".format(docs_from_cbl))
    # print "n1ql docs found ", docs_from_n1ql
    for doc in docs_from_cbl:
        assert doc in docs_from_n1ql
    # assert docs_from_cbl == docs_from_n1ql

    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4", [
    ("type", "hotel", "country", "United States", "country", "France", "vacancy", True),
])
def test_query_where_and_or(params_from_base_test_setup, whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key, whr_val, select_property1, select_property2, like_key, like_val", [
    ("type", "landmark", "country", "name", "name", "Royal Engineers Museum"),
    ("type", "landmark", "country", "name", "name", "Royal engineers museum"),
    ("type", "landmark", "country", "name", "name", "eng%e%"),
    ("type", "landmark", "country", "name", "name", "Eng%e%"),
    ("type", "landmark", "country", "name", "name", "%eng____r%"),
    ("type", "landmark", "country", "name", "name", "%Eng____r%"),
])
def test_query_pattern_like(params_from_base_test_setup, whr_key, whr_val, select_property1, select_property2, like_key, like_val):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("whr_key, whr_val, select_property1, select_property2, regex_key, regex_val", [
    ("type", "landmark", "country", "name", "name", '\\bEng.*e\\b'),
    ("type", "landmark", "country", "name", "name", "\\beng.*e\\b"),
])
def test_query_pattern_regex(params_from_base_test_setup, whr_key, whr_val, select_property1, select_property2, regex_key, regex_val):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, limit", [
    ("name", 100),
])
def test_query_isNullOrMissing(params_from_base_test_setup, select_property1, limit):
    """ @summary
    Fetches docs with where email is null or missing

    let searchQuery = Query
        .select(SelectResult.expression(Expression.meta().id),
                SelectResult.expression(Expression.property("name")))
        .from(DataSource.database(db))
        .where(Expression.property("email").isNullOrMissing())

    Verifies with n1ql - select meta().id from `travel-sample` t where meta().id not like "_sync%" and (t.name IS NULL or t.name IS MISSING)
    """
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, whr_key, whr_val", [
    ("title", "type", "hotel"),
])
def test_query_ordering(params_from_base_test_setup, select_property1, whr_key, whr_val):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, select_property2, substring", [
    ("email", "name", "gmail.com"),
])
def test_query_substring(params_from_base_test_setup, select_property1, select_property2, substring):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    log_info("docs_from_n1ql: {}".format(docs_from_n1ql))

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")


@pytest.mark.parametrize("select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to", [
    ("name", "type", "hotel", "country", "France", "Le Clos Fleuri"),
])
def test_query_collation(params_from_base_test_setup, select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to):
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
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    base_url = params_from_base_test_setup["base_url"]
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
    query = N1QLQuery(n1ql_query)
    docs_from_n1ql = []

    for row in sdk_client.n1ql_query(query):
        docs_from_n1ql.append(row)

    assert len(docs_from_cbl) == len(docs_from_n1ql)
    log_info("Found {} docs".format(len(docs_from_cbl)))
    assert sorted(docs_from_cbl) == sorted(docs_from_n1ql)
    log_info("Doc contents match")
