import time
import itertools

from lib.user import User
from lib.admin import Admin

from cluster_setup import cluster
import pytest

@pytest.mark.sanity
def test_1(cluster):

    cluster.reset("sync_gateway_default.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC"])

    users = admin.get_users()

    seth = users["seth"]
    adam = users["adam"]
    traun = users["traun"]

    seth.add_docs(1000, uuid_names=True)  # ABC
    adam.add_docs(3000, uuid_names=True, bulk=True)  # ABC
    traun.add_docs(6000, uuid_names=True, bulk=True)  # ABC

    assert len(seth.cache) == 1000
    assert len(adam.cache) == 3000
    assert len(traun.cache) == 6000

    # discuss appropriate time with team
    time.sleep(10)

    # verify number of changes
    seth_changes_doc_ids = seth.get_doc_ids_from_changes()
    print("seth number of changes: {}".format(len(seth_changes_doc_ids)))
    assert len(seth_changes_doc_ids) == 10000

    adam_changes_doc_ids = adam.get_doc_ids_from_changes()
    print("adam number of changes: {}".format(len(adam_changes_doc_ids)))
    assert len(adam_changes_doc_ids) == 10000

    traun_changes_doc_ids = traun.get_doc_ids_from_changes()
    print("traun number of changes: {}".format(len(traun_changes_doc_ids)))
    assert len(traun_changes_doc_ids) == 10000

    #verify id of docs
    seth_ids = list(itertools.chain(seth.cache.keys(), adam.cache.keys(), traun.cache.keys()))
    adam_ids = list(itertools.chain(seth.cache.keys(), adam.cache.keys(), traun.cache.keys()))
    traun_ids = list(itertools.chain(seth.cache.keys(), adam.cache.keys(), traun.cache.keys()))

    assert set(seth_changes_doc_ids) == set(seth_ids)
    assert set(adam_changes_doc_ids) == set(adam_ids)
    assert set(traun_changes_doc_ids) == set(traun_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))



