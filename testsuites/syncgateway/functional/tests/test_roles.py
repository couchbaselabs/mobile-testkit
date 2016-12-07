import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.role
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_roles_sanity(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'roles_sanity'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("sg_conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    mode = cluster.reset(sg_config_path=sg_conf)

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
