import pytest
import json

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.document import create_docs
from keywords import document


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
def test_design_doc_update(setup_client_syncgateway_test):
    """
    1. Create some documents on the client
    2. Create design doc version 1
    3. Run a query and check for expected results with design doc version 1
    4. Update design doc to version 2
    5. Run a query and check for expected results with design doc version 2
    -> CBL 1.4.0 or earlier fails to update design doc to version 2.
    """

    log_info("Running 'test_design_doc_update'")

    ls_url = setup_client_syncgateway_test["ls_url"]
    log_info("ls_url: {}".format(ls_url))

    client = MobileRestClient()

    ls_url = setup_client_syncgateway_test["ls_url"]

    num_content_docs_per_db = 10
    num_no_content_docs_per_db = 5
    d_doc_name = "dd"
    ls_db = client.create_database(ls_url, name="ls_db")

    for i in range(num_content_docs_per_db):
        doc_id = "doc_content_{}".format(i)
        doc_body_1 = document.create_doc(doc_id=doc_id, content={"hi": "I should be in the view"})
        log_info(doc_body_1)
        doc_1 = client.add_doc(url=ls_url, db=ls_db, doc=doc_body_1)

    for i in range(num_no_content_docs_per_db):
        doc_id = "doc_no_content_{}".format(i)
        doc_body_2 = document.create_doc(doc_id=doc_id)
        log_info(doc_body_2)
        doc_2 = client.add_doc(url=ls_url, db=ls_db, doc=doc_body_2)

    view = """{
    "language" : "javascript",
    "views" : {
        "content_view" : {
            "map" : "function(doc, meta) { if (doc.content) { emit(doc._id, doc._rev); } }"
        }
    }
}"""

    design_doc_id = client.add_design_doc(url=ls_url, db=ls_db, name=d_doc_name, doc=view)
    ddoc = client.get_doc(url=ls_url, db=ls_db, doc_id=design_doc_id)

    content_view_rows_1 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    log_info("content_view_rows: {}, ddoc: {}".format(content_view_rows_1, ddoc))

    client.verify_view_row_num(view_response=content_view_rows_1, expected_num_rows=10)

    view = """{
    "language" : "javascript",
    "views" : {
        "content_view" : {
            "map" : "function(doc, meta) { if (!(doc.content)) { emit(doc._rev); } }"
        }
    }
}"""

    content_view_rows_2 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    log_info("content_view_rows_2: {}, ddoc: {}".format(content_view_rows_2, ddoc))

    client.verify_view_row_num(view_response=content_view_rows_2, expected_num_rows=5)
