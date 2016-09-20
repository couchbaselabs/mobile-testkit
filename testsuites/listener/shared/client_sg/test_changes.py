import pytest

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker
from keywords.SyncGateway import SyncGateway

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_longpoll_changes_termination_timeout(setup_client_syncgateway_test):
    """https://github.com/couchbase/couchbase-lite-java-core/issues/1296
    1. Create 30 longpoll _changes in a loop (with timeout parameter = 5s)
    2. Cancel the request after 2s
    3. Wait 5.1s
    4. Create another request GET /db/ on listener and make sure the listener responds
    """

    ls_db = "ls_db"
    sg_url = setup_client_syncgateway_test["sg_url"]
    ls_url = setup_client_syncgateway_test["ls_url"]

    log_info("Running 'test_longpoll_changes_termination' ...")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_url: {}".format(sg_url))

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(url=sg_url, config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS))

    client = MobileRestClient()
    client.create_database(ls_url, ls_db)

    ct = ChangesTracker(ls_url, ls_db)

    with ThreadPoolExecutor(max_workers=35) as executor:

        futures = [executor.submit(
            ct.start,
            timeout=5000,
            request_timeout=2000
        ) for _ in range(30)]

        for futures in as_completed(futures):
            log_info("Future _changes loop complete")

    log_info("Futures exited")

    # make sure client can still take connections
    dbs = client.get_databases(url=ls_url)
    log_info(dbs)
    database = client.get_database(url=ls_url, db_name=ls_db)
    log_info(database)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.usefixtures("setup_client_syncgateway_suite")
def test_longpoll_changes_termination_heartbeat(setup_client_syncgateway_test):
    """https://github.com/couchbase/couchbase-lite-java-core/issues/1296
    Create 30 longpoll _changes in a loop (with heartbeat parameter = 5s)
    Cancel the request after 2s
    Wait 5.1s
    Create another request GET /db/ on listener and make sure the listener responds
    """

    log_info("Running 'longpoll_changes_termination' ...")

    ls_db = "ls_db"
    sg_url = setup_client_syncgateway_test["sg_url"]
    ls_url = setup_client_syncgateway_test["ls_url"]

    log_info("Running 'test_longpoll_changes_termination' ...")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_url: {}".format(sg_url))

    sg_helper = SyncGateway()
    sg_helper.start_sync_gateway(url=sg_url, config="{}/walrus.json".format(SYNC_GATEWAY_CONFIGS))

    client = MobileRestClient()
    client.create_database(ls_url, ls_db)

    ct = ChangesTracker(ls_url, ls_db)

    with ThreadPoolExecutor(max_workers=35) as executor:
        futures = [executor.submit(
            ct.start,
            timeout=5000,
            heartbeat=5000,
            request_timeout=2000
        ) for _ in range(30)]

        for futures in as_completed(futures):
            log_info("Future _changes loop complete")

    log_info("Futures exited")

    # make sure client can still take connections
    dbs = client.get_databases(url=ls_url)
    log_info(dbs)
    database = client.get_database(url=ls_url, db_name=ls_db)
    log_info(database)










