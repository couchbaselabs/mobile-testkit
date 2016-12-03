import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords import document


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_raw_attachment(setup_client_syncgateway_test):
    """
    1.  Add Text attachment to sync_gateway
    2.  Try to get the raw attachment
    Pass: It is possible to get the raw attachment
    """

    log_info("Running 'test_raw_attachment'")

    ls_url = setup_client_syncgateway_test["ls_url"]
    log_info("ls_url: {}".format(ls_url))

    client = MobileRestClient()

    ls_db = client.create_database(ls_url, name="ls_db")

    ls_user_channels = ["NBC"]

    doc_with_att = document.create_doc(
        doc_id="att_doc",
        content={
            "sample_key": "sample_val"
        },
        attachment_name="sample_text.txt",
        channels=ls_user_channels
    )

    doc = client.add_doc(
        url=ls_url,
        db=ls_db,
        doc=doc_with_att
    )

    att = client.get_attachment(
        url=ls_url,
        db=ls_db,
        doc_id=doc["id"],
        attachment_name="sample_text.txt"
    )

    expected_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\nDuis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.\nExcepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."

    assert expected_text == att


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
@pytest.mark.skip(reason="https://github.com/couchbase/couchbase-lite-net/issues/749")
def test_inline_large_attachments(setup_client_syncgateway_test):
    """
    1.  Start LiteServ and Sync Gateway
    2.  Create 2 databases on LiteServ (ls_db1, ls_db2)
    3.  Start continuous push replication from ls_db1 to sg_db
    4.  Start continuous pull replication from sg_db to ls_db2
    5.  PUT 5 large inline attachments to ls_db1
    6.  DELETE the docs on ls_db1
    7.  PUT same 5 large inline attachments to ls_db1
    8.  Verify docs replicate to ls_db2
    9.  Purge ls_db1
    10. Verify docs removed
    """

    log_info("Running 'test_inline_large_attachments' ...")

    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_url_admin = setup_client_syncgateway_test["sg_admin_url"]

    ls_url = setup_client_syncgateway_test["ls_url"]

    log_info("ls_url: {}".format(ls_url))
    log_info("sg_url: {}".format(sg_url))
    log_info("sg_url_admin: {}".format(sg_url_admin))

    ls_db1 = "ls_db1"
    ls_db2 = "ls_db2"
    sg_db = "db"

    client = MobileRestClient()
    client.create_database(ls_url, ls_db1)
    client.create_database(ls_url, ls_db2)

    # Start continuous push replication from ls_db1 -> sg_db
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db1,
        to_url=sg_url, to_db=sg_db
    )

    # Start continuous push replication from sg_db -> ls_db2
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url, from_db=sg_db,
        to_db=ls_db2
    )

    # doc with 2.36 PNG attachment
    attachment_docs = []
    for i in range(5):
        doc = document.create_doc(
            doc_id="large_attach_{}".format(i),
            attachment_name="golden_gate_large.jpg",
            channels=["ABC"]
        )
        attachment_docs.append(doc)

    # add large attachments to ls_db1
    docs = []
    for doc in attachment_docs:
        docs.append(client.add_doc(ls_url, ls_db1, doc, use_post=False))

    # Delete docs
    client.delete_docs(ls_url, ls_db1, docs)
    client.verify_docs_deleted(ls_url, ls_db1, docs)

    # Recreated docs
    recreated_docs = []
    for doc in attachment_docs:
        recreated_docs.append(client.add_doc(ls_url, ls_db1, doc, use_post=False))

    client.verify_docs_present(ls_url, ls_db1, recreated_docs)
    client.verify_docs_present(sg_url, sg_db, recreated_docs)
    client.verify_docs_present(ls_url, ls_db2, recreated_docs)

    purged_docs = client.purge_docs(ls_url, ls_db1, recreated_docs)
    log_info(purged_docs)

    # All purged docs should have replicated and should be gone now.
    # This is currently failing due to some docs not replicating to ls_db2
    client.verify_docs_deleted(ls_url, ls_db1, recreated_docs)
    client.verify_docs_deleted(sg_url, sg_db, recreated_docs)
    client.verify_docs_deleted(ls_url, ls_db2, recreated_docs)
