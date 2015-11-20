import time

import pytest
import concurrent.futures

from lib.admin import Admin

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_sanity(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 100

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")
    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync before docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    kdwb_doc_ids = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_doc_ids.extend(doc_pusher.cache.keys())

    dj_0.verify_ids_from_changes(100, kdwb_doc_ids)


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_sanity_backfill(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 100

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")

    kdwb_doc_ids = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_doc_ids.extend(doc_pusher.cache.keys())

    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync after docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    dj_0.verify_ids_from_changes(100, kdwb_doc_ids)
