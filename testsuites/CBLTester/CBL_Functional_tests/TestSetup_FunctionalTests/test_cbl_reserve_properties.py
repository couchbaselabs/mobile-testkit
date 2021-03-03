import pytest

from CBLClient.FileLogging import FileLogging
from CBLClient.Document import Document
from keywords import document
from keywords import attachment


@pytest.mark.listener
@pytest.mark.properties
def test_reserve_property(params_from_base_test_setup):
    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    if liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with CBL version below 3.0.0')
    channel = ["Replication-1"]
    doc_id = "doc_1"
    documentObj = Document(base_url)
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channel, expiry=2, attachments=attachment.generate_2_png_10_10())
    doc1 = documentObj.create(doc_id, doc_body)
    assert "Illegal top-level key `_id` in document" in db.saveDocument(cbl_db, doc1), \
        "Did not throw the reserve property error"
