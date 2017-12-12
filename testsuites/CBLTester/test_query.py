from libraries.data.doc_generators import simple_user
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query


def test_get_doc_ids():
    # This rest end point runs the below query
    # let query = Query
    #                .select(SelectResult.expression(Expression.meta().id))
    #                .from(DataSource.database(database))
    base_url = "http://10.17.0.152:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Add 10 docs
    docs = {}
    doc_ids = []
    for i in range(10):
        doc_id = "doc_{}".format(i)
        doc_ids.append(doc_id)
        docs[doc_id] = simple_user()

    db.saveDocuments(source_db, docs)

    ids_from_db = db.getDocIds(source_db)
    assert len(ids_from_db) == len(doc_ids)

    for d in doc_ids:
        assert d in ids_from_db


def test_simple_query():
    # Select First Name from DB where City = "MV"
    # Create select_prop - PropertyExpression using "FN"
    # Create SelectResult.expression(select_prop)
    # Create from_prop - DatabaseSource from_prop"
    # Create whr_key_prop - PropertyExpression using "whr_key_prop"
    # create query using select_prop, from_prop, whr_key_prop and whr_val
    # Run query
    # Query result
    # Runs the below query
    # let query = Query
    #   .select(SelectResult.expression(select_prop))
    #   .from(from_prop)
    #   .where(
    #         whr_key_prop.equalTo(whr_val)
    #       )
    base_url = "http://10.17.0.152:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    doc = {
        "doc1": {
            "First Name": "abc",
            "Last Name": "xyz",
            "City": "MV"
        }
    }

    log_info("Saving the documents")
    db.saveDocuments(database=source_db, documents=doc)

    qy = Query(base_url)
    select_string = "First Name"
    select_prop = qy.query_expression_property(select_string)
    from_prop = qy.query_datasource_database(source_db)
    whr_string = "City"
    whr_val = "MV"
    whr_prop = qy.query_expression_property(whr_string)
    query = qy.query_create(select_prop, from_prop, whr_prop, whr_val)
    query_result = qy.query_run(query)
    result = qy.query_next_result(query_result)
    while result:
        result_string = qy.query_result_string(result, select_string)
        result = qy.query_next_result(query_result)
        assert result_string == "abc"
