import time

import pytest
import concurrent.futures

from lib.admin import Admin

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_roles_sanity(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    tv_stations = ["ABC", "CBS", "NBC"]

    number_of_djs = 10
    number_of_vjs = 10

    number_of_docs_per_pusher = 100

    admin = Admin(cluster.sync_gateways[0])

    # djs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="dj", number=number_of_djs, password="password")
    # vjs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="vj", number=number_of_vjs, password="password")

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")

    # mogul = admin.register_user(target=cluster.sync_gateways[0], db="db", name="mogul", password="password", roles=["tv_stations", "radio_stations"])

    radio_doc_ids = []
    # for radio_station in radio_stations:
    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format("KDWB_pusher"), password="password", channels=["KDWB"])
    doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
    radio_doc_ids.extend(doc_pusher.cache.keys())
    #    radio_doc_ids.extend(doc_pusher.cache.keys())

    dj_0.verify_ids_from_changes(100, radio_doc_ids)

    # tv_doc_ids = []
    # for tv_station in tv_stations:
    #     doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(tv_station), password="password", channels=[tv_station])
    #     doc_pusher.add_docs(number_of_docs_per_pusher, uuid_names=True, bulk=True)
    #     tv_doc_ids.extend(doc_pusher.cache.keys())
    #
    # # Verify djs get docs for all the channels associated with the radio_stations role
    # expected_num_radio_docs = len(radio_stations) * number_of_docs_per_pusher
    # for dj in djs:
    #     dj.verify_ids_from_changes(expected_num_radio_docs, radio_doc_ids)
    #
    # # Verify vjs get docs for all the channels associated with the tv_stations role
    # expected_num_tv_docs = len(tv_stations) * number_of_docs_per_pusher
    # for vj in vjs:
    #     vj.verify_ids_from_changes(expected_num_tv_docs, tv_doc_ids)
    #
    # # Verify mogul gets docs for all the channels associated with the radio_stations + tv_stations roles
    # all_doc_ids = list(radio_doc_ids)
    # all_doc_ids.extend(tv_doc_ids)
    # mogul.verify_ids_from_changes(expected_num_radio_docs + expected_num_tv_docs, all_doc_ids)

# TODO - Add role mid scenario
# TODO - Delete role mid scenario
# TODO - Update role mid scenario
