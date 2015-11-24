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

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        assert docs == expected_docs
        log.info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))

    # Verify that
    # user created doc-ids exist in docs received in changes feed
    # expected revision is equal to received revision
    expected_revision = str(num_revisions + 1)
    docs_rev_dict = in_parallel(user_objects, 'get_num_revisions')
    rev_errors = []
    for user_obj, docs_revision_dict in docs_rev_dict.items():
        for doc_id in docs_revision_dict.keys():
            rev = docs_revision_dict[doc_id]
            log.info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log.error('User {} doc_id got revision {}, expected revision {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))

    assert len(rev_errors) == 0
    # verify all user created sub-set doc-ids present in
    # received super-set doc-ids
    #for user_obj in user_objects:
    #    super_set = user_obj.
    end = time.time()
    print("TIME:{}s".format(end - start))






