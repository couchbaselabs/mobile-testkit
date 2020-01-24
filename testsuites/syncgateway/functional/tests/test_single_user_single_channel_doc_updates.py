import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes
import libraries.testkit.settings

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from utilities.cluster_config_utils import get_sg_version, persist_cluster_config_environment_prop, copy_to_temp_conf

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
@pytest.mark.parametrize("sg_conf_name, num_docs, num_revisions, x509_cert_auth", [
    ("sync_gateway_default_functional_tests", 100, 100, False),
    ("sync_gateway_default_functional_tests_no_port", 100, 100, True),
    ("sync_gateway_default_functional_tests_couchbase_protocol_withport_11210", 100, 100, False)
])
def test_single_user_single_channel_doc_updates(params_from_base_test_setup, sg_conf_name, num_docs,
                                                num_revisions, x509_cert_auth):
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
    if "sync_gateway_default_functional_tests_couchbase_protocol_withport_11210" in sg_conf_name and (ssl_enabled or mode.lower() == "di"):
        pytest.skip('ssl enabled so cannot run with couchbase protocol')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log.info("Running 'single_user_single_channel_doc_updates'")
    log.info("cluster_conf: {}".format(cluster_conf))
    log.info("sg_conf: {}".format(sg_conf))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    start = time.time()
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        cluster_conf = temp_cluster_config
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
