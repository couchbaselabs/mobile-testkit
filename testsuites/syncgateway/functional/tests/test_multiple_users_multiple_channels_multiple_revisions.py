import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster

from libraries.testkit.parallelize import in_parallel

from keywords.utils import log_info
from keywords.utils import log_error
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from utilities.cluster_config_utils import get_sg_version, persist_cluster_config_environment_prop, copy_to_temp_conf


# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796
@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions, x509_cert_auth", [
    ("sync_gateway_default_functional_tests", 10, 3, 10, 10, False),
    ("sync_gateway_default_functional_tests_no_port", 10, 3, 10, 10, True),
    pytest.param("sync_gateway_default_functional_tests_couchbase_protocol_withport_11210", 10, 3, 10, 10, False, marks=pytest.mark.sanity)
])
def test_mulitple_users_mulitiple_channels_mulitple_revisions(params_from_base_test_setup, sg_conf_name, num_users,
                                                              num_channels, num_docs, num_revisions, x509_cert_auth):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

    # Skip the test if ssl disabled as it cannot run without port using http protocol
    if ("sync_gateway_default_functional_tests_no_port" in sg_conf_name) and get_sg_version(cluster_conf) < "1.5.0":
        pytest.skip('couchbase/couchbases ports do not support for versions below 1.5')
    if "sync_gateway_default_functional_tests_no_port" in sg_conf_name and not ssl_enabled:
        pytest.skip('ssl disabled so cannot run without port')

    # Skip the test if ssl enabled as it cannot run using couchbase protocol
    # TODO : https://github.com/couchbaselabs/sync-gateway-accel/issues/227
    # Remove DI condiiton once above bug is fixed
    if "sync_gateway_default_functional_tests_couchbase_protocol_withport_11210" in sg_conf_name and \
            (ssl_enabled or mode.lower() == "di"):
        pytest.skip('ssl enabled so cannot run with couchbase protocol')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'mulitple_users_mulitiple_channels_mulitple_revisions'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))
    log_info("num_users: {}".format(num_users))
    log_info("num_channels: {}".format(num_channels))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revisions: {}".format(num_revisions))

    start = time.time()

    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        cluster_conf = temp_cluster_config

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log_info("Add docs")
    bulk = True
    in_parallel(user_objects, 'add_docs', num_docs, bulk)

    # Update docs
    log_info("Update docs")
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
        log_info('User {} got {} docs, expected docs: {}'.format(user_obj.name, docs, expected_docs))
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
            log_info('User {} doc_id {} has {} revisions, expected revision: {}'.format(user_obj.name,
                                                                                        doc_id, rev, expected_revision))
            if rev != expected_revision:
                rev_errors.append(doc_id)
                log_error('User {} doc_id {} got revision {}, expected revision {}'.format(
                    user_obj.name,
                    doc_id,
                    rev,
                    expected_revision)
                )

    assert len(rev_errors) == 0

    # Verify each User created docs are part of changes feed
    output = in_parallel(user_objects, 'check_doc_ids_in_changes_feed')
    assert True in output.values()

    end = time.time()
    log_info("Test ended.")
    log_info("Main test duration: {}".format(end - init_completed))
    log_info("Test setup time: {}".format(init_completed - start))
    log_info("Total Time taken: {}s".format(end - start))
