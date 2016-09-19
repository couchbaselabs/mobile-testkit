import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.autoprune
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_auto_prune_listener_sanity(setup_client_syncgateway_test):
    """Sanity test for the autoprune feature

    1. Create a db and put a doc
    2. Update the docs past the default revs_limit (20)
    3. Assert the the docs only retain 20 revs
    """

    ls_url = setup_client_syncgateway_test["ls_url"]
    client = MobileRestClient()

    log_info("Running 'test_auto_prune_listener_sanity' ...")
    log_info("ls_url: {}".format(ls_url))

    num_docs = 1
    num_revs = 100

    ls_db = client.create_database(url=ls_url, name="ls_db")
    docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs, id_prefix="ls_db_doc")
    updated_docs = client.update_docs(url=ls_url, db=ls_db, docs=docs, number_updates=num_revs)

    client.verify_max_revs_num_for_docs(url=ls_url, db=ls_db, docs=docs, expected_max_number_revs_per_doc=20)



