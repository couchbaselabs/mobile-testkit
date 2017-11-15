import time
import json

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from CBLClient.Utils import Release


def test_replication():
    source_db = None
    base_url = "http://192.168.1.8:8989"
    db = Database(base_url)
    # SG URL
    sg_db = "db"
    cbl_db = "test_db"
    sg_ip = "192.168.33.23"
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)
    sg_admin_url = "http://{}:4985".format(sg_ip)

    # Create CBL database
    source_db = db.database_create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = db.database_getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    # A bulk add API is needed
    # The below approach is not scalable
    dn = Dictionary(base_url)
    dictionary = dn.dictionary_create()
    dn.dictionary_put(dictionary, "FirstName", "abc")
    dn.dictionary_put(dictionary, "LastName", "xyz")
    dn.dictionary_put(dictionary, "City", "MV")
    dn.dictionary_put(dictionary, "State", "CA")

    doc = Document(base_url)
    document = doc.document_create(id="foo", dictionary=dictionary)
    log_info("Document is {}".format(document))
    db.database_save(source_db, document)

    # Add docs to SG
    sg_client = MobileRestClient()
    num_docs = 10
    sg_client.add_docs(
        url=sg_admin_url,
        db=sg_db,
        number=num_docs,
        id_prefix="test_changes"
    )

    # Start and stop continuous replication
    replicator = Replication(target_url)
    repl = replicator.configure_replication(source_db, target_url)
    log_info("repl: {}".format(repl))
    replicator.start_replication(repl)
    time.sleep(5)
    replicator.stop_replication(repl)

    all_docs = sg_client.get_all_docs(
        url=sg_admin_url,
        db=sg_db
    )

    # Verify database doc counts
    cbl_doc_count = db.database_docCount(source_db)
    assert len(all_docs["rows"]) == num_docs + 1
    assert cbl_doc_count == num_docs + 1

    # Check that all doc ids in SG are also present in CBL
    for i in all_docs["rows"]:
        assert db.database_contains(source_db, str(i["id"]))


def test_query():
    source_db = None
    base_url = "http://10.17.1.4:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    source_db = db.database_create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = db.database_getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    # A bulk add API is needed
    # The below approach is not scalable
    dn = Dictionary(base_url)
    dictionary = dn.dictionary_create()
    dn.dictionary_put(dictionary, "FirstName", "abc")
    dn.dictionary_put(dictionary, "LastName", "xyz")
    dn.dictionary_put(dictionary, "City", "MV")
    dn.dictionary_put(dictionary, "State", "CA")

    doc = Document(base_url)
    document = doc.document_create(id="foo", dictionary=dictionary)
    log_info("Document is {}".format(document))
    db.database_save(source_db, document)

    # select FirstName from test_db where City = "MV"
    # Expression property for select
    qy = Query(base_url)

    select_prop = qy.query_expression_property(prop="FirstName")
    dbsource_prop = qy.query_datasource_database(database=source_db)
    whr_key_prop = qy.query_expression_property(prop="City")
    whr_val = "MV"

    result_set = qy.query_run(select_prop, dbsource_prop, whr_key_prop, whr_val)

    query_result = qy.query_next_result(result_set)
    key = "FirstName"
    expected_val = "abc"
    while query_result:
        output = qy.query_result_string(query_result, key)
        assert output == expected_val
        query_result = qy.query_next_result(result_set)

    rel = Release(base_url)
    rel.release(
        [
            result_set,
            source_db,
            document,
            dictionary,
            select_prop,
            dbsource_prop,
            whr_key_prop
        ]
    )


def test_adddocs():
    source_db = None
    base_url = "http://10.17.1.4:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    source_db = db.database_create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = db.database_getName(source_db)
    assert db_name == "test_db"

    sample_doc = {
        "a": {
            "c": "d",
            "e": "f"
        },
        "b": {
            "g": "h",
            "i": "j"
        }
    }

    db.database_addDocuments(source_db, sample_doc)
    doc_count = db.database_docCount(source_db)
    db_path = db.database_path(source_db)
    log_info("doc_count: {}".format(doc_count))
    log_info("db_path: {}".format(db_path))
    assert doc_count == 2

    doc_ids = db.database_getDocIds(source_db)
    log_info("doc_ids: {}".format(doc_ids))

    docs = db.database_getDocuments(source_db)
    log_info("docs: {}".format(json.dumps(docs)))

    db.database_delete(cbl_db, db_path)
