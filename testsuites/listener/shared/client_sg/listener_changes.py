import time

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def start_changes_tracking(url, db):
    ct = ChangesTracker(url, db)
    ct.start(timeout=5000)
    return ct

def longpoll_changes_termination(ls_url, cluster_config):
    log_info("ls_url: {}".format(ls_url))
    log_info("cluster_config: {}".format(cluster_config))
    log_info("Running 'longpoll_changes_termination' ...")

    ls_db = "ls_db"
    sg_url = cluster_config["sync_gateways"][0]["admin"]

    client = MobileRestClient()
    client.create_database(ls_url, ls_db)

    with ThreadPoolExecutor(max_workers=35) as executor:

        futures = [executor.submit(
            start_changes_tracking,
            ls_url,
            ls_db

        ) for _ in range(30)]

        time.sleep(2)

        for future in as_completed(futures):
            future.stop()










