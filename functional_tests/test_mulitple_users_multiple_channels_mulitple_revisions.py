import time
import pytest
from lib.user import User
import concurrent.futures
from lib.admin import Admin
from fixtures import cluster
import pytest
from lib.parallelize import *
import logging
log = logging.getLogger('test_framework')



# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

@pytest.mark.sanity
@pytest.mark.distributed_index
@pytest.mark.parametrize("num_users", [5])
@pytest.mark.parametrize("num_channels", [3]) #all users share all channels
@pytest.mark.parametrize("num_docs", [2])
@pytest.mark.parametrize("num_revisions", [10])
def test_mulitple_users_mulitiple_channels_mulitple_revisions(cluster, num_users,num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    start = time.time()

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    users = ["User-" + str(i) for i in range(num_users)]
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    user_objects = []
    use_uuid_names = True

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    for username in users:
        user_obj = admin.register_user(target=sgs[0], db="db", name=username, password=password, channels=channels)
        user_objects.append(user_obj)

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs, use_uuid_names)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)

    end = time.time()
    print("TIME:{}s".format(end - start))






