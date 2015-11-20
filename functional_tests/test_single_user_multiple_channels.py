import time
from lib.admin import Admin
import pytest

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_single_user_single_channel(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC", "CBS", "NBC", "FOX"])

    # Round robin
    count = 1
    num_sgs = len(cluster.sync_gateways)
    while count <= 20:
        seth.add_docs(100, bulk=True)
        seth.target = cluster.sync_gateways[count % num_sgs]
        count += 1

    assert len(seth.cache) == 2000

    print(seth)

    time.sleep(10)

    seth_cache_ids = seth.cache.keys()
    seth.verify_ids_from_changes(2000, seth_cache_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))

