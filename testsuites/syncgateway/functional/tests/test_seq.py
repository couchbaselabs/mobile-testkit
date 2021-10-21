import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes
from requests import Session
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from utilities.cluster_config_utils import get_sg_version, persist_cluster_config_environment_prop, copy_to_temp_conf
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config


@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, num_users, num_docs, num_revisions, x509_cert_auth", [
    ("sync_gateway_default_functional_tests", 10, 500, 1, False),
    ("sync_gateway_default_functional_tests_no_port", 10, 500, 1, True),
    pytest.param("sync_gateway_default_functional_tests_couchbase_protocol_withport_11210", 10, 500, 1, False, marks=[pytest.mark.sanity, pytest.mark.oscertify])
])
def test_seq(params_from_base_test_setup, sg_conf_name, num_users, num_docs, num_revisions, x509_cert_auth):
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

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_conf = temp_cluster_config

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
    doc_seq = user_0_changes["results"][num_docs // 2]["seq"]

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


@pytest.mark.syncgateway
@pytest.mark.prometheus
def test_metrics_public_ports(params_from_base_test_setup):
    """
    @summary:
    1. set up metrics config on sgw config
    2. Access some of the public api with metrics port
    3. Verify it is not accessible
    """
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    # Skip the test if sgw version is not 2.8.3 and above
    if sync_gateway_version < "2.8.3":
        pytest.skip('this test requires version 2.8.3 and above')

    session = Session()
    sg_db = "db"
    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # 1. set up metrics config on sgw config
    metrics_url = sg_admin_url.replace("4985", "4986")

    # 2. Access some of the public api with metrics port
    req = session.get("{}/{}".format(metrics_url, sg_db))
    # 3. Verify it is not accessible
    assert req.status_code == 404, "Expected 404 status, actual {}".format(req.status_code)

    req = session.get("{}/{}/_config".format(metrics_url, sg_db))
    assert req.status_code == 404, "Expected 404 status, actual {}".format(req.status_code)

    req = session.get("{}/_config".format(metrics_url))
    assert req.status_code == 404, "Expected 404 status, actual {}".format(req.status_code)

    req = session.get("{}/_all_docs".format(metrics_url))
    assert req.status_code == 404, "Expected 404 status, actual {}".format(req.status_code)


@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("sync_gateway_default_functional_tests", True)
])
def test_remove_dcp_cacert_handling(params_from_base_test_setup, sg_conf_name, x509_cert_auth):
    """
    @summary
    1. Set up default sync config file
    2. Generate x509
    3. Add cacertpath without keypath and certpath, but add username/password on the sgw config file
    4. Verify SGW starts succesfully without keypath and certpath
    """

    # 1. Set up default sync config file
    cluster_conf = params_from_base_test_setup["cluster_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    mode = params_from_base_test_setup["mode"]

    # Skip the test if sgw version is below 2.8.2
    if sync_gateway_version <= "2.8.2":
        pytest.skip('this cannot run with sgw version below 2.8.2')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    disable_tls_server = params_from_base_test_setup["disable_tls_server"]

    # 2. Generate x509
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_conf = temp_cluster_config

    # 3. Add cacertpath without keypath and certpath, but add username/password on the sgw config file
    cluster = Cluster(config=cluster_conf)
    cbs_bucket = cluster.servers[0].get_bucket_names()[0]
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ username }}", '"username": "{}",'.format(cbs_bucket))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ password }}", '"password": "password",')
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ certpath }}", "")
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ keypath }}", "")

    # 4. Verify SGW starts succesfully without keypath and certpath
    cluster.reset(sg_config_path=temp_sg_config)  # this has an assert to verify SGW can start successfully with above setup
