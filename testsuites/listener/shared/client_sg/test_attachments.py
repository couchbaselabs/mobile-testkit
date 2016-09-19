import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.Document import Document

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

    doc_helper = Document()

    doc_with_att = doc_helper.create_doc(
        id="att_doc",
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
