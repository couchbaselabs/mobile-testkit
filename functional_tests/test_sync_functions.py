import time

import pytest
import concurrent.futures

from lib.admin import Admin

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_sync_functions_1(cluster):

    cluster.reset(config="sync_gateway_custom_sync_one.json")

    admin = Admin(cluster.sync_gateways[0])
    admin.create_role("db", "radio_stations", ["KMOW", "HWOD", "KDWB"])
    admin.create_role("db", "tv_stations", ["ABC", "CBS", "NBC"])

    djs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="dj", number=10, password="password", roles=["radio_stations"])
    vjs = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="vj", number=10, password="password", roles=["tv_stations"])

    doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="doc_pusher", password="password", channels=["KMOW"])
    doc_pusher.add_docs(10, uuid_names=True, bulk=True)

# TODO - Add role mid scenario
# TODO - Delete role mid scenario
# TODO - Update role mid scenario