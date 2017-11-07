import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords.CBLTestCase import TestCase


def test_document_with_id():
    base_url = "http://10.17.1.59:8989"
    tc = TestCase(base_url)
    document = tc.document_create(id="foo")
    doc_id = tc.document_getId(document)

    assert doc_id == "foo"


def test_document_with_dict():
    base_url = "http://10.17.1.59:8989"
    tc = TestCase(base_url)
    dictionary = tc.dictionary_create()
    tc.dictionary_put(dictionary, "foo", "bar")
    document = tc.document_create(id="foo", dictionary=dictionary)

    doc_id = tc.document_getId(document)
    doc_string = tc.document_getString(document, "foo")

    assert doc_id == "foo"
    assert doc_string == "bar"


def test_replication():
    source_db = None
    base_url = "http://192.168.1.8:8989"
    tc = TestCase(base_url)
    # SG URL
    sg_db = "sg_db1"
    cbl_db = "test_db"
    sg_ip = "192.168.33.23"
    target_url = "blip://{}:4985/{}".format(sg_ip, sg_db)
    sg_admin_url = "http://{}:4985".format(sg_ip)

    # Create CBL database
    source_db = tc.database_create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = tc.database_getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    # A bulk add API is needed
    # The below approach is not scalable
    dictionary = tc.dictionary_create()
    tc.dictionary_put(dictionary, "FirstName", "abc")
    tc.dictionary_put(dictionary, "LastName", "xyz")
    tc.dictionary_put(dictionary, "City", "MV")
    tc.dictionary_put(dictionary, "State", "CA")
    document = tc.document_create(id="foo", dictionary=dictionary)
    log_info("Document is {}".format(document))
    tc.database_save(source_db, document)

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
    repl = tc.configure_replication(source_db, target_url)
    log_info("repl: {}".format(repl))
    tc.start_replication(repl)
    time.sleep(5)
    tc.stop_replication(repl)

    all_docs = sg_client.get_all_docs(
        url=sg_admin_url,
        db=sg_db
    )

    # Verify database doc counts
    cbl_doc_count = tc.database_docCount(source_db)
    assert len(all_docs["rows"]) == num_docs + 1
    assert cbl_doc_count == num_docs + 1

    # Check that all doc ids in SG are also present in CBL
    for i in all_docs["rows"]:
        assert tc.database_contains(source_db, str(i["id"]))


def test_query():
    source_db = None
    base_url = "http://10.17.1.59:8989"
    tc = TestCase(base_url)
    cbl_db = "test_db"

    # Create CBL database
    source_db = tc.database_create(cbl_db)
    log_info("Database is {}".format(source_db))
    db_name = tc.database_getName(source_db)
    assert db_name == "test_db"

    # Add a doc to CBL
    # A bulk add API is needed
    # The below approach is not scalable
    dictionary = tc.dictionary_create()
    tc.dictionary_put(dictionary, "FirstName", "abc")
    tc.dictionary_put(dictionary, "LastName", "xyz")
    tc.dictionary_put(dictionary, "City", "MV")
    tc.dictionary_put(dictionary, "State", "CA")
    document = tc.document_create(id="foo", dictionary=dictionary)
    log_info("Document is {}".format(document))
    tc.database_save(source_db, document)

    # select FirstName from test_db where City = "MV"
    select = "FirstName"
    frm = source_db
    whr_key = "City"
    whr_val = "MV"
    rows = tc.run_query(select, frm, whr_key, whr_val)
    log_info("rows: {}".format(rows))
