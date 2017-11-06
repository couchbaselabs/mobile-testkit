import sys
import pytest

from keywords.CBLRestClient import CBLRestClient
from keywords.utils import log_info
from keywords.CBLMemoryPointer import MemoryPointer
from keywords.CBLTestCase import TestCase


def test_database():
    client = CBLRestClient()
    database = None
    url = "http://10.17.1.77:8989"

    try:
        database = client.database_create(url, "foo")
        log_info("database created: {}".format(database))
        assert database

        db_name = client.database_getName(url, database)
        log_info("database name: {}".format(db_name))
        assert db_name == "\"foo\""
    except Exception:
        log_info("Caught exception {}".format(sys.exc_info()[0]))
        raise
    finally:
        client.release(url, database)


def test_document_with_id():
    base_url = "http://192.168.1.8:8989"
    tc = TestCase(base_url)
    document = tc.document_create(id="foo")
    doc_id = tc.document_getId(document)

    assert doc_id == "foo"


def test_document_with_dict():
    base_url = "http://192.168.1.8:8989"
    tc = TestCase(base_url)
    dictionary = tc.dictionary_create();
    tc.dictionary_put(dictionary, "foo", "bar")
    document = tc.document_create("foo", dictionary)

    doc_id = tc.document_getId(document);
    doc_string = tc.document_getString(document, "foo")

    assert doc_id == "foo"
    assert doc_string == "bar"
