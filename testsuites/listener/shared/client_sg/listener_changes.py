import time

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def longpoll_changes_termination_timeout(ls_url, cluster_config):
    log_info("ls_url: {}".format(ls_url))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("Running 'longpoll_changes_termination' ...")

    ls_db = "ls_db"
    sg_url = cluster_config["sync_gateways"][0]["admin"]

    client = MobileRestClient()
    client.create_database(ls_url, ls_db)

    ct = ChangesTracker(ls_url, ls_db)

    with ThreadPoolExecutor(max_workers=35) as executor:

        futures = [executor.submit(
            ct.start,
            timeout=5000,
            request_timeout=2000
        ) for _ in range(30)]

    log_info("Futures exited")

    # make sure client can still take connections
    dbs = client.get_databases(url=ls_url)
    log_info(dbs)
    database = client.get_database(url=ls_url, db_name=ls_db)
    log_info(database)


def longpoll_changes_termination_heartbeat(ls_url, cluster_config):
    log_info("ls_url: {}".format(ls_url))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("Running 'longpoll_changes_termination' ...")

    ls_db = "ls_db"
    sg_url = cluster_config["sync_gateways"][0]["admin"]

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

    log_info("Futures exited")

    # make sure client can still take connections
    dbs = client.get_databases(url=ls_url)
    log_info(dbs)
    database = client.get_database(url=ls_url, db_name=ls_db)
    log_info(database)










