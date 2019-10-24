import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from utilities.cluster_config_utils import get_sg_version, persist_cluster_config_environment_prop


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.role
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.bulkops
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("sync_gateway_default_functional_tests", True),
    ("sync_gateway_default_functional_tests_no_port", False),
    ("sync_gateway_default_functional_tests_couchbase_protocol_withport_11210", True)
])
def test_roles_sanity(params_from_base_test_setup, sg_conf_name, x509_cert_auth):

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

    log_info("Running 'roles_sanity'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    persist_cluster_config_environment_prop(cluster_conf, 'x509_certs', x509_cert_auth)

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    tv_stations = ["ABC", "CBS", "NBC"]

    number_of_djs = 10
    number_of_vjs = 10

    number_of_docs_per_pusher = 500

    admin = Admin(cluster.sync_gateways[0])

    admin.create_role("db", name="radio_stations", channels=radio_stations)
    admin.create_role("db", name="tv_stations", channels=tv_stations)

    djs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="dj", number=number_of_djs, password="password", roles=["radio_stations"])
    vjs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="vj", number=number_of_vjs, password="password", roles=["tv_stations"])

    mogul = admin.register_user(target=cluster.sync_gateways[0], db="db", name="mogul", password="password", roles=["tv_stations", "radio_stations"])

    radio_doc_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        radio_doc_caches.append(doc_pusher.cache)

    radio_docs = {k: v for cache in radio_doc_caches for k, v in cache.items()}

    tv_doc_caches = []
    for tv_station in tv_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(tv_station), password="password", channels=[tv_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        tv_doc_caches.append(doc_pusher.cache)

    tv_docs = {k: v for cache in tv_doc_caches for k, v in cache.items()}

    # Verify djs get docs for all the channels associated with the radio_stations role
    expected_num_radio_docs = len(radio_stations) * number_of_docs_per_pusher
    verify_changes(djs, expected_num_docs=expected_num_radio_docs, expected_num_revisions=0, expected_docs=radio_docs)

    # Verify vjs get docs for all the channels associated with the tv_stations role
    expected_num_tv_docs = len(tv_stations) * number_of_docs_per_pusher
    verify_changes(vjs, expected_num_docs=expected_num_tv_docs, expected_num_revisions=0, expected_docs=tv_docs)

    # Verify mogul gets docs for all the channels associated with the radio_stations + tv_stations roles
    all_docs_caches = list(radio_doc_caches)
    all_docs_caches.extend(tv_doc_caches)
    all_docs = {k: v for cache in all_docs_caches for k, v in cache.items()}
    verify_changes(mogul, expected_num_docs=expected_num_radio_docs + expected_num_tv_docs, expected_num_revisions=0, expected_docs=all_docs)


# TODO - Add role mid scenario
# TODO - Delete role mid scenario
# TODO - Update role mid scenario
