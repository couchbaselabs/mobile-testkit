import pytest

from CBLClient.Document import Document
from keywords import document
from keywords import attachment


@pytest.mark.listener
@pytest.mark.properties
def test_reserve_property(params_from_base_test_setup):
    """
    @summary:
    1. Create docs in CBL using the _id
    2. Make sure _id is not supported while creating the doc .
    3. In future releases _exp, _attachments will not be supported too, then we need to update the same test
    """

    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    # liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with CBL version below 3.0.0')
    channel = ["Replication-1"]
    doc_id = "doc_1"
    documentObj = Document(base_url)
    # Creating a doucment with _id
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channel, expiry=2,
                                   attachments=attachment.generate_2_png_10_10())
    doc1 = documentObj.create(doc_id, doc_body)
    try:
        db.saveDocument(cbl_db, doc1)
        assert False, "Did not throw the unsupported reserve property error"
    except Exception as err:
        assert "Illegal top-level key `_id` in document" in str(err), \
            "Did not throw the unsupported reserve property error"

    # This is added to catch the
    doc_body = document.create_doc(doc_id="doc_2", content="doc2", channels=channel, cbl=True, expiry=2,
                                   attachments=attachment.generate_2_png_10_10())

    doc2 = documentObj.create("doc_2", doc_body)
    db.saveDocument(cbl_db, doc2)
    # if "c-" in liteserv_platform:
    #     try:
    #         db.saveDocument(cbl_db, doc2)
    #         assert False, "Did not throw the unsupported reserve property error"
    #     except Exception as err:
    #         assert "Illegal top-level key `_id` in document" in str(err), \
    #             "Did not throw the unsupported reserve property error"
    # else:
    #     db.saveDocument(cbl_db, doc2)
