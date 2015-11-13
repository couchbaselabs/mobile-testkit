import time
import itertools

from lib.user import User
from lib.admin import Admin

from cluster_setup import cluster
import pytest

@pytest.mark.sanity
def test_1(cluster):

    cluster.reset("sync_gateway_default_functional_tests.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["NBC", "CBS"])
    admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])

    users = admin.get_users()

    seth = users["seth"]
    adam = users["adam"]
    traun = users["traun"]

    # TODO use bulk docs
    seth.add_docs(2356, uuid_names=True)  # ABC
    adam.add_docs(8198, uuid_names=True)  # NBC, CBS
    traun.add_docs(2999, uuid_names=True)  # ABC, NBC, CBS

    assert len(seth.cache) == 2356
    assert len(adam.cache) == 8198
    assert len(traun.cache) == 2999

    # discuss appropriate time with team
    time.sleep(10)

    #verify id of docs
    expected_seth_ids = list(itertools.chain(seth.cache.keys(), traun.cache.keys()))
    expected_adam_ids = list(itertools.chain(adam.cache.keys(), traun.cache.keys()))
    expected_traun_ids = list(itertools.chain(seth.cache.keys(), adam.cache.keys(), traun.cache.keys()))

    seth.verify_ids_from_changes(expected_seth_ids)
    adam.verify_ids_from_changes(expected_adam_ids)
    traun.verify_ids_from_changes(expected_traun_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))



