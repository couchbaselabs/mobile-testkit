import time
import pytest
from testkit.user import User
import concurrent.futures
from testkit.admin import Admin
from fixtures import cluster
import pytest
from testkit.parallelize import *
import logging
log = logging.getLogger(settings.LOGGER)



# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

@pytest.mark.sanity
@pytest.mark.distributed_index
@pytest.mark.parametrize(
        "conf, num_users, num_channels, num_docs, num_revisions", [
            ("sync_gateway_default_functional_tests_di.json", 10, 3, 10, 10),
            ("sync_gateway_default_functional_tests_cc.json", 10, 3, 10, 10)
        ],
        ids=["DI-1", "CC-1"]
)
def test_mulitple_users_mulitiple_channels_mulitple_revisions(cluster, conf, num_users, num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    log.info("conf: {}".format(conf))
    log.info("num_users: {}".format(num_users))
    log.info("num_channels: {}".format(num_channels))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    start = time.time()

    mode = cluster.reset(config_path=conf)

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    users = ["User-" + str(i) for i in range(num_users)]
    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    user_objects = []
    use_uuid_names = True

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

    # Adding sleep to let sg to catch-up...
    # Without sleep this test fails in Channel-Cache mode and changes feed doesn't return the expected
    # num_revisions in docs.
    # The test passes in Distributed-Index mode.
    time.sleep(10)

    # Get changes for all users
    in_parallel(user_objects, 'get_changes')

    # every user should have same number of docs
    # total/expected docs = num_users * num_docs
    recieved_docs = in_parallel(user_objects, 'get_num_docs')

    expected_docs = num_users * num_docs
    for user_obj, docs in recieved_docs.items():
        log.info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
        assert docs == expected_docs


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

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in output.values()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    log.info("Test ended.")
    log.info("Main test duration: {}".format(end - init_completed))
    log.info("Test setup time: {}".format(init_completed - start))
    log.info("Total Time taken: {}s".format(end - start))






