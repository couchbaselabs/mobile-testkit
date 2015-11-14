import time
from lib.admin import Admin
import pytest

from fixtures import cluster

@pytest.mark.sanity
def test_1(cluster):

    cluster.reset("sync_gateway_default_functional_tests.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    users = admin.get_users()

    seth = users["seth"]
    admin = users["admin"]

    seth.add_docs(7000, uuid_names=True)
    admin.add_docs(3000, uuid_names=True)

    assert len(seth.cache) == 7000
    assert len(admin.cache) == 3000

    print(seth)
    print(admin)

    time.sleep(10)

    seth_cache_ids = seth.cache.keys()
    seth.verify_ids_from_changes(7000, seth_cache_ids)

    # Admin should have doc ids from seth + admin
    admin_cache_ids = admin.cache.keys()
    admin_cache_ids.extend(seth_cache_ids)

    admin.verify_ids_from_changes(10000, admin_cache_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))

