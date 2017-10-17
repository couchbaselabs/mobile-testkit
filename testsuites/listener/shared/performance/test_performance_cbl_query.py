import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from keywords.document import create_docs
# This test has to run when new ios version arrives atleast once.


@pytest.mark.listener
def test_view_query_performance(setup_client_syncgateway_test):
    """
     Run this test when new iOS version arrives to make sure CBL query is not diminishing
    1. Add 100000 docs to the client with content
    2. Create design doc version 1 to fetch doc._id, doc._rev for docs with content
    3. Update docs 3 times which gets revision number 4-
    4. Run a query and check for 100000 expected docs with design doc version 1
    3. Verify the performance of the view query did not diminish.
    """

    log_info("Running 'test_design_doc_update'")

    ls_url = setup_client_syncgateway_test["ls_url"]
    log_info("ls_url: {}".format(ls_url))

    client = MobileRestClient()

    ls_url = setup_client_syncgateway_test["ls_url"]

    num_content_docs_per_db = 10000
    d_doc_name = "dd"
    ls_db = client.create_database(ls_url, name="ls_db")

    # Add 100000 docs to the client with content
    bulk_docs_content = create_docs("doc_content_", num_content_docs_per_db, content={"hi": "I should be in the view"})
    ls_db_docs1 = client.add_bulk_docs(url=ls_url, db=ls_db, docs=bulk_docs_content)
    assert len(ls_db_docs1) == num_content_docs_per_db

    client.update_docs(url=ls_url, db=ls_db, docs=ls_db_docs1, number_updates=3, delay=0.1)
    # Design doc to to fetch doc._id, doc._rev for docs with content
    view = """{
    "language" : "javascript",
    "views" : {
        "content_view" : {
            "map" : "function(doc, meta) { if (doc.content) { emit(doc._id, doc._rev); } }"
        }
    }
}"""

    client.add_design_doc(url=ls_url, db=ls_db, name=d_doc_name, doc=view)
    start = time.time()
    content_view_rows_1 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    finish = time.time()
    assert finish - start < 5
    client.verify_view_row_num(view_response=content_view_rows_1, expected_num_rows=10000)
