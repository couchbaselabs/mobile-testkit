import pytest

from keywords.constants import SYNC_GATEWAY_CONFIGS

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import SyncGateway


@pytest.mark.sanity
@pytest.mark.listener
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


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.autoprune
@pytest.mark.replication
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_auto_prune_with_pull(setup_client_syncgateway_test):
    """Sanity test for autopruning with replication

    1. Create a database on LiteServ (ls_db)
    2. Add doc to sync gateway
    3. Update doc 50 times on sync_gateway
    4. Set up pull replication from sync_gateway db to LiteServ db
    5. Verify number of revisions on client is default (20)
    """

    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_url = setup_client_syncgateway_test["sg_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]

    client = MobileRestClient()
    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(url=sg_url, config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS))

    log_info("Running 'test_auto_prune_listener_sanity' ...")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_url: {}".format(sg_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))

    num_docs = 1
    num_revs = 50

    sg_user_channels = ["NBC"]
    sg_db = "db"
    sg_user_name = "sg_user"

    sg_user = client.create_user(url=sg_admin_url, db=sg_db, name=sg_user_name, password="password", channels=sg_user_channels)
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)

    ls_db = client.create_database(url=ls_url, name="ls_db")

    sg_db_docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=num_docs,
        id_prefix=sg_db,
        channels=sg_user_channels,
        auth=sg_session
    )

    sg_docs_update = client.update_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_db_docs,
        number_updates=num_revs,
        auth=sg_session
    )

    # Start continuous replication ls_db <- sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_admin_url,
        from_db=sg_db,
        to_db=ls_db
    )

    client.wait_for_replication_status_idle(url=ls_url, replication_id=repl_one)
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=sg_docs_update)
    client.verify_revs_num_for_docs(url=ls_url, db=ls_db, docs=sg_docs_update, expected_revs_per_doc=20)


