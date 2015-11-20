import time
from lib.admin import Admin
import pytest

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_1(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin_user = admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    seth.add_docs(7000)
    admin_user.add_docs(3000)

    assert len(seth.cache) == 7000
    assert len(admin_user.cache) == 3000

    print(seth)
    print(admin_user)

    time.sleep(10)

    seth_cache_ids = seth.cache.keys()
    seth.verify_ids_from_changes(7000, seth_cache_ids)

    # Admin should have doc ids from seth + admin
    admin_cache_ids = admin_user.cache.keys()
    admin_cache_ids.extend(seth_cache_ids)

    admin_user.verify_ids_from_changes(10000, admin_cache_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))

