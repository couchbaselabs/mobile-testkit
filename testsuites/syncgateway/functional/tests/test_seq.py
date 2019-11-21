import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from utilities.cluster_config_utils import get_sg_version


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions", [
    ("sync_gateway_default_functional_tests", 10, 500, 1),
    ("sync_gateway_default_functional_tests_no_port", 10, 500, 1),
    ("sync_gateway_default_functional_tests_couchbase_protocol_withport_11210", 10, 500, 1)
])
def test_seq(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions):

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

    log_info("Running seq")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))
    log_info("num_users: {}".format(num_users))
    log_info("num_docs: {}".format(num_docs))
    log_info("num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    admin = Admin(cluster.sync_gateways[0])

    # all users will share docs due to having the same channel
    users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="user", number=num_users, password="password", channels=["ABC"])

    for user in users:
        user.add_docs(num_docs, bulk=True)

    for user in users:
        user.update_docs(num_revisions)

    time.sleep(5)

    user_0_changes = users[0].get_changes(since=0)
    doc_seq = user_0_changes["results"][num_docs / 2]["seq"]

    # https://github.com/couchbase/sync_gateway/issues/1475#issuecomment-172426052
    # verify you can issue _changes with since=12313-0::1023.15
    for user in users:
        changes = user.get_changes(since=doc_seq)
        log_info("Trying changes with since={}".format(doc_seq))
        assert len(changes["results"]) > 0

        second_to_last_doc_entry_seq = changes["results"][-2]["seq"]
        last_doc_entry_seq = changes["results"][-1]["seq"]

        log_info('Second to last doc "seq": {}'.format(second_to_last_doc_entry_seq))
        log_info('Last doc "seq": {}'.format(last_doc_entry_seq))

        if mode == "di":
            # Verify last "seq" follows the formate 12313-0, not 12313-0::1023.15
            log_info('Verify that the last "seq" is a plain hashed value')
            assert len(second_to_last_doc_entry_seq.split("::")) == 2
            assert len(last_doc_entry_seq.split("::")) == 1
        elif mode == "cc":
            assert second_to_last_doc_entry_seq > 0
            assert last_doc_entry_seq > 0
        else:
            raise ValueError("Unsupported 'mode' !!")

    all_doc_caches = [user.cache for user in users]
    all_docs = {k: v for cache in all_doc_caches for k, v in list(cache.items())}
    verify_changes(users, expected_num_docs=num_users * num_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)
