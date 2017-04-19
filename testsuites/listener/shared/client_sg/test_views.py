import pytest

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info

from keywords import document
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.views
@pytest.mark.session
def test_stale_revision_should_not_be_in_the_index(setup_client_syncgateway_test):
    """original ticket: https://github.com/couchbase/couchbase-lite-android/issues/855

    scenario:
    1. Running sync_gateway
    2. Create database and starts both push and pull replicators through client REST API
    3. Create two or more views through client REST API
    4. Add doc, and verify doc is index with current revision through client REST API
    5. Make sure document is pushed to sync gateway through sync gateway REST API
    6. Update doc with sync gateway (not client side) through sync gateway REST API
    7. Make sure updated document is pull replicated to client  through client REST API
    8. Make sure updated document is indexed through client REST API
    9. Make sure stale revision is deleted from index.  through client REST API
    10. Pass criteria
    """

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    num_docs = 10
    num_revs = 100

    d_doc_name = "dd"
    sg_db = "db"
    sg_user_name = "sg_user"

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("Running 'test_stale_revision_should_not_be_in_the_index'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revs: {}".format(num_revs))

    client = MobileRestClient()

    sg_user_channels = ["NBC"]
    client.create_user(url=sg_admin_url, db=sg_db, name=sg_user_name, password="password", channels=sg_user_channels)
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)

    view = """{
    "language" : "javascript",
    "views" : {
        "content_view" : {
            "map" : "function(doc, meta) { if (doc.content) { emit(doc._id, doc._rev); } }"
        },
        "update_view" : {
            "map" : "function(doc, meta) { emit(doc.updates, null); }"
        }
    }
}"""

    ls_db = client.create_database(url=ls_url, name="ls_db")

    # Setup continuous push / pull replication from ls_db1 to sg_db
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db,
        to_url=sg_admin_url, to_db=sg_db
    )

    client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url, from_db=sg_db,
        to_db=ls_db
    )

    design_doc_id = client.add_design_doc(url=ls_url, db=ls_db, name=d_doc_name, doc=view)
    client.get_doc(url=ls_url, db=ls_db, doc_id=design_doc_id)

    doc_body = document.create_doc(doc_id="doc_1", content={"hi": "I should be in the view"}, channels=sg_user_channels)

    log_info(doc_body)

    doc_body_2 = document.create_doc(doc_id="doc_2", channels=sg_user_channels)

    doc = client.add_doc(url=ls_url, db=ls_db, doc=doc_body)
    doc_2 = client.add_doc(url=ls_url, db=ls_db, doc=doc_body_2)

    content_view_rows = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    client.verify_view_row_num(view_response=content_view_rows, expected_num_rows=1)

    update_view_rows = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="update_view")
    client.verify_view_row_num(view_response=update_view_rows, expected_num_rows=2)

    expected_docs_list = [doc, doc_2]
    client.verify_docs_present(url=sg_url, db=sg_db, expected_docs=expected_docs_list, auth=sg_session)

    updated_doc = client.update_doc(url=sg_url, db=sg_db, doc_id=doc["id"], number_updates=10, auth=sg_session)

    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=updated_doc)

    content_view_rows_2 = client.get_view(url=ls_url, db=ls_db, design_doc_name=d_doc_name, view_name="content_view")
    client.verify_view_row_num(view_response=content_view_rows_2, expected_num_rows=1)

    client.verify_view_contains_keys(view_response=content_view_rows_2, keys=doc["id"])
    client.verify_view_contains_values(view_response=content_view_rows_2, values=updated_doc["rev"])
