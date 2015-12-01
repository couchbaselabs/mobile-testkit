import time

import pytest
import concurrent.futures

from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_sanity(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 5000

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")
    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync before docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    kdwb_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_caches.append(doc_pusher.cache)

    # Build global doc_id, rev dict for all docs from all KDWB caches
    kdwb_docs = {k: v for cache in kdwb_caches for k, v in cache.items()}

    # wait for changes
    time.sleep(5)

    # Make sure dj_0 sees KDWB docs in _changes feed
    verify_changes(dj_0, expected_num_docs=number_of_docs_per_pusher, expected_num_revisions=0, expected_docs=kdwb_docs)


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_sanity_backfill(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 5000

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")

    kdwb_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_caches.append(doc_pusher.cache)

    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync after docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    # Build global doc_id, rev dict for all docs from all KDWB caches
    kdwb_docs = {k: v for cache in kdwb_caches for k, v in cache.items()}

    # wait for changes
    time.sleep(5)

    verify_changes(dj_0, expected_num_docs=number_of_docs_per_pusher, expected_num_revisions=0, expected_docs=kdwb_docs)


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_require_roles(cluster):

    cluster.reset(config="sync_gateway_custom_sync_require_roles.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    tv_stations = ["ABC", "CBS", "NBC"]

    number_of_djs = 10
    number_of_vjs = 10

    number_of_docs_per_pusher = 100

    admin = Admin(cluster.sync_gateways[0])

    admin.create_role("db", name="radio_stations", channels=radio_stations)
    admin.create_role("db", name="tv_stations", channels=tv_stations)

    djs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="dj", number=number_of_djs, password="password", roles=["radio_stations"])
    vjs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="vj", number=number_of_vjs, password="password", roles=["tv_stations"])

    mogul = admin.register_user(target=cluster.sync_gateways[0], db="db", name="mogul", password="password", roles=["tv_stations", "radio_stations"])

    radio_doc_ids = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station], roles=["radio_stations"])
        doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
        radio_doc_ids.extend(doc_pusher.cache.keys())

    tv_doc_ids = []
    for tv_station in tv_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(tv_station), password="password", channels=[tv_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
        tv_doc_ids.extend(doc_pusher.cache.keys())

    # Verify djs get docs for all the channels associated with the radio_stations role
    expected_num_radio_docs = len(radio_stations) * number_of_docs_per_pusher
    for dj in djs:
        dj.verify_ids_from_changes(expected_num_radio_docs, radio_doc_ids)

    # Verify vjs get docs for all the channels associated with the tv_stations role
    expected_num_tv_docs = len(tv_stations) * number_of_docs_per_pusher
    for vj in vjs:
        vj.verify_ids_from_changes(expected_num_tv_docs, tv_doc_ids)

    # Verify mogul gets docs for all the channels associated with the radio_stations + tv_stations roles
    all_doc_ids = list(radio_doc_ids)
    all_doc_ids.extend(tv_doc_ids)
    mogul.verify_ids_from_changes(expected_num_radio_docs + expected_num_tv_docs, all_doc_ids)
