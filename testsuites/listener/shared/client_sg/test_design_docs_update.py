import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.document import create_docs


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
def test_design_doc_update(setup_client_syncgateway_test):
    """
    Ref: https://github.com/couchbase/couchbase-lite-android/issues/1139
    https://github.com/couchbaselabs/mobile-testkit/issues/1155
    1. Add 10 docs to the client with content
    2. Add 5 docs to the client without content
    2. Create design doc version 1 to fetch doc._id, doc._rev for docs with content
    3. Run a query and check for 10 expected docs with design doc version 1
    4. Update design doc to version 2 to fetch doc._id, doc._rev for docs with no content
    5. Run a query and check for 5 expected docs with design doc version 2
    -> With CBL 1.4.0 or earlier, even though design doc is updated to version 2,
       the second query will use design doc 1 and return 10 docs instead of 5
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

    # Add 10 docs to the client with content
    bulk_docs_content = create_docs("doc_content_", num_content_docs_per_db, content={"hi": "I should be in the view"})
    ls_db_docs1 = client.add_bulk_docs(url=ls_url, db=ls_db, docs=bulk_docs_content)
    assert len(ls_db_docs1) == num_content_docs_per_db

    # Add 5 docs to the client without content
    bulk_docs_no_content = create_docs("doc_no_content_", num_no_content_docs_per_db)
    ls_db_docs2 = client.add_bulk_docs(url=ls_url, db=ls_db, docs=bulk_docs_no_content)
    assert len(ls_db_docs2) == num_no_content_docs_per_db

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
    content_view_rows_1 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    client.verify_view_row_num(view_response=content_view_rows_1, expected_num_rows=10)

    # Design doc to to fetch doc._id, doc._rev for docs with no content
    view = """{
    "language" : "javascript",
    "views" : {
        "content_view" : {
            "map" : "function(doc, meta) { if (!(doc.content)) { emit(doc._id, doc._rev); } }"
        }
    }
}"""

    dd_rev = client.get_design_doc_rev(url=ls_url, db=ls_db, name=d_doc_name)
    log_info("dd_rev: {}".format(dd_rev))

    client.update_design_doc(url=ls_url, db=ls_db, name=d_doc_name, doc=view, rev=dd_rev)
    content_view_rows_2 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    client.verify_view_row_num(view_response=content_view_rows_2, expected_num_rows=5)
