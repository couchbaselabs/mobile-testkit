import time
import pytest
from lib.user import User
import concurrent.futures
from lib.admin import Admin
from fixtures import cluster
from lib.web_server import WebServer
import pytest
from lib.parallelize import *
import logging
log = logging.getLogger(settings.LOGGER)



# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

@pytest.mark.sanity
@pytest.mark.distributed_index
@pytest.mark.parametrize("num_users", [5])
@pytest.mark.parametrize("num_channels", [1]) #all users share all channels
@pytest.mark.parametrize("num_docs", [1])
@pytest.mark.parametrize("num_revisions", [1])
def test_bucket_online_offline_webhooks(cluster, num_users,num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    start = time.time()

    cluster.reset(config="sync_gateway_webhook.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(120)
    ws.stop()
    log.info(ws.get_data())