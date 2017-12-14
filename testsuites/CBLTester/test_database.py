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


def test_documents():
    source_db = None
    base_url = "http://10.17.0.152:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    log_info("Creating a Database {}".format(cbl_db))
    source_db = db.create(cbl_db)
    log_info("Getting the database name")
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    doc = {
        "doc1": {
            "name": "abc",
            "place": "xyz"
        },
        "doc2": {
            "name": "def",
            "place": "ghi"
        }
    }

    log_info("Saving the documents")
    db.saveDocuments(database=source_db, documents=doc)
    doc_ids = ["doc1", "doc2"]
    log_info("Getting the documents")
    doc_resp = db.getDocuments(source_db, doc_ids)
    assert doc == doc_resp


def test_replication():
    source_db = None
    base_url = "http://10.17.5.92:8989"
    db = Database(base_url)
    # SG URL
    sg_db = "db"
    cbl_db = "test_db"
    sg_ip = "192.168.33.11"
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)
    sg_admin_url = "http://{}:4985".format(sg_ip)

    # Create CBL database
    source_db = db.create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    # A bulk add API is needed
    # The below approach is not scalable
    dn = Dictionary(base_url)
    dictionary = dn.create()
    dn.setString(dictionary, "FirstName", "abc")
    dn.setString(dictionary, "LastName", "xyz")
    dn.setString(dictionary, "City", "MV")
    dn.setString(dictionary, "State", "CA")

    doc = Document(base_url)
    document = doc.create(doc_id="foo", dictionary=dictionary)
    log_info("Document is {}".format(document))
    db.save(source_db, document)

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
    replicator = Replication(base_url)
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
    cbl_doc_count = db.getCount(source_db)
    assert len(all_docs["rows"]) == num_docs + 1
    assert cbl_doc_count == num_docs + 1

    # Check that all doc ids in SG are also present in CBL
    for i in all_docs["rows"]:
        assert db.contains(source_db, str(i["id"]))


def test_query():
    source_db = None
    base_url = "http://192.168.1.2:8989"
    db = Database(base_url)
    cbl_db = "test_db"

    # Create CBL database
    source_db = db.create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = db.getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    doc = {
        "doc1": {
            "name": "abc",
            "place": "xyz"
        }
    }

    db.saveDocuments(database=source_db, documents=doc)

    # select FirstName from test_db where City = "MV"
    # Expression property for select
    qy = Query(base_url)

    select_prop = qy.query_expression_property(prop="FirstName")
    dbsource_prop = qy.query_datasource_database(database=source_db)
    whr_key_prop = qy.query_expression_property(prop="City")
    whr_val = "MV"

    query = qy.query_create(select_prop, dbsource_prop, whr_key_prop, whr_val)
    result_set = qy.query_run(query)

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
            select_prop,
            dbsource_prop,
            whr_key_prop
        ]
    )
