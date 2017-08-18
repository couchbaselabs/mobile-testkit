import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes
import libraries.testkit.settings

from keywords.SyncGateway import sync_gateway_config_path_for_mode

import logging
log = logging.getLogger(libraries.testkit.settings.LOGGER)


# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_docs, num_revisions", [
    ("sync_gateway_default_functional_tests", 100, 100),
    ("sync_gateway_default_functional_tests_no_port", 100, 100),
    ("sync_gateway_default_functional_tests_couchbase_port", 100, 100)

])
def test_single_user_single_channel_doc_updates(params_from_base_test_setup, sg_conf_name, num_docs, num_revisions):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

    # Skip the test if ssl disabled as it cannot run without port using http protocol
    if "sync_gateway_default_functional_tests_no_port" in sg_conf_name and not ssl_enabled:
        pytest.skip('ssl disabled so cannot run without port')

    # Skip the test if ssl enabled as it cannot run without port using couchbases protocol
    if "sync_gateway_default_functional_tests_couchbase_port" in sg_conf_name and ssl_enabled:
        pytest.skip('ssl enabled so cannot run with couchbase protocol')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log.info("Running 'single_user_single_channel_doc_updates'")
    log.info("cluster_conf: {}".format(cluster_conf))
    log.info("sg_conf: {}".format(sg_conf))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    start = time.time()

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    num_docs = num_docs
    num_revisions = num_revisions
    username = "User-1"
    password = "password"
    channels = ["channel-1"]

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    single_user = admin.register_user(target=sgs[0], db="db", name=username, password=password, channels=channels)

    # Not using bulk docs
    single_user.add_docs(num_docs, name_prefix="test-")

    assert len(single_user.cache) == num_docs

    # let SG catch up with all the changes
    time.sleep(5)

    single_user.update_docs(num_revisions)

    time.sleep(10)

    verify_changes([single_user], expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=single_user.cache)

    end = time.time()
    log.info("TIME:{}s".format(end - start))
