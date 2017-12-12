import time

from libraries.data.doc_generators import simple_user
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
from CBLClient.Replication import Replication


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
    # Select "First Name" from DB where City = "MV"
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
    # Create select_prop - PropertyExpression using "First Name"
    # Create SelectResult.expression(select_prop)
    select_string = "First Name"
    select_prop = qy.query_expression_property(select_string)

    # Create from_prop - DatabaseSource from_prop"
    from_prop = qy.query_datasource_database(source_db)

    # Create whr_key_prop - PropertyExpression using "whr_key_prop"
    whr_string = "City"
    whr_val = "MV"
    whr_prop = qy.query_expression_property(whr_string)

    # create query using select_prop, from_prop, whr_key_prop and whr_val
    query = qy.query_create(select_prop, from_prop, whr_prop, whr_val)
    # Run query
    query_result = qy.query_run(query)
    # Query result
    result = qy.query_next_result(query_result)
    while result:
        result_string = qy.query_result_string(result, select_string)
        result = qy.query_next_result(query_result)
        assert result_string == "abc"


def test_query_whr_and_or():
    # Select "First Name" from DB where City = "MV"
    # Runs the below query
    #  let searchQuery = Query
    #         .select(SelectResult.expression(Expression.meta().id))
    #         .from(DataSource.database(db))
    #         .where(Expression.property("type").equalTo("hotel")
    #             .and(Expression.property("country").equalTo("United States")
    #                 .or(Expression.property("country").equalTo("France")))
    #                 .and(Expression.property("vacancy").equalTo(true)))

    base_url = "http://10.17.0.152:8989"
    db = Database(base_url)
    sg_db = "db"
    cbl_db = "test_db"
    sg_ip = "192.168.33.22"
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)
    sg_admin_url = "http://{}:4985".format(sg_ip)

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Start and stop continuous replication
    replicator = Replication(base_url)
    repl = replicator.configure_replication(source_db, target_url)
    log_info("repl: {}".format(repl))
    replicator.start_replication(repl)

    time.sleep(10)
    qy = Query(base_url)
    # Create SelectResult.expression(Expression.meta().id)
    log_info("Creating select expression")
    meta_id_prop = qy.query_expression_meta_id()
    select_result_expression = qy.query_select_result_expression_create(meta_id_prop)

    # Create DataSource.database(db)
    log_info("Creating DataSource expression")
    from_prop = qy.query_datasource_database(source_db)

    # Create Expression.property("type").equalTo("hotel")
    log_info("Creating type hotel expression")
    type_string = "type"
    type_val = "hotel"
    type_prop = qy.query_expression_property(type_string)
    hotel_equal_to = qy.create_equalTo_expression(type_prop, type_val)

    # Create Expression.property("country").equalTo("United States")
    log_info("Creating country United States expression")
    us_country_string = "country"
    us_country_val = "United States"
    us_country_prop = qy.query_expression_property(us_country_string)
    us_equal_to = qy.create_equalTo_expression(us_country_prop, us_country_val)

    # Expression.property("country").equalTo("France")
    log_info("Creating country France expression")
    fr_country_string = "country"
    fr_country_val = "United States"
    fr_country_prop = qy.query_expression_property(fr_country_string)
    fr_equal_to = qy.create_equalTo_expression(fr_country_prop, fr_country_val)

    # Create Expression.property("vacancy").equalTo(true)
    log_info("Creating vacancy true expression")
    vc_string = "vacancy"
    vc_val = True
    vc_prop = qy.query_expression_property(vc_string)
    vc_equal_to = qy.create_equalTo_expression(vc_prop, vc_val)

    # Create and expression - hotel_equal_to and us_equal_to
    log_info("Creating and expression")
    whr_exp_1 = qy.create_and_expression(hotel_equal_to, us_equal_to)

    # Create or expression - whr_exp_1 or fr_equal_to
    log_info("Creating or expression")
    whr_exp_2 = qy.create_and_expression(whr_exp_1, fr_equal_to)

    # Create and expression - whr_exp_2 or vc_equal_to
    log_info("Creating and expression")
    whr_exp_3 = qy.create_and_expression(whr_exp_2, vc_equal_to)

    # create query using select_expression, from_prop, whr_exp_3
    log_info("Creating query expression")
    query = qy.query_create(select_result_expression, from_prop, whr_exp_3)

    # Run query
    log_info("Creating DataSource expression")
    query_result = qy.query_run(query)

    # Query result
    result = qy.query_next_result(query_result)
    result_strings = []
    while result:
        result_string = qy.query_result_string(result, "id")
        result = qy.query_next_result(query_result)
        result_strings.append(result_string)

    log_info(result_strings)
