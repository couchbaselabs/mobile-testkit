import time
from lib.admin import Admin

from cluster_setup import cluster


def test_1(cluster):

    cluster.reset("sync_gateway_default.json")

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

    seth_changes_doc_ids = seth.get_doc_ids_from_changes()
    print("seth number of changes: {}".format(len(seth_changes_doc_ids)))

    seth_cache_ids = seth.cache.keys()

    assert len(seth_changes_doc_ids) == 7000
    assert len(seth_changes_doc_ids) == len(seth_cache_ids)

    assert set(seth_changes_doc_ids) == set(seth_changes_doc_ids)

    admin_changes_doc_ids = admin.get_doc_ids_from_changes()
    print("admin number of changes: {}".format(len(admin_changes_doc_ids)))

    assert len(admin_changes_doc_ids) == 10000
    admin_cache_ids = admin.cache.keys()

    # Admin should have doc ids from seth + admin
    admin_cache_ids.extend(seth_cache_ids)

    assert set(admin_changes_doc_ids) == set(admin_cache_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))

