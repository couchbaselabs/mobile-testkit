import time
import itertools

from lib.user import User
from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster
import pytest

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_multiple_users_single_channel(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    sgs = cluster.sync_gateways

    # TODO parametrize
    num_docs_seth = 10
    num_docs_adam = 20
    num_docs_traun = 30

    admin = Admin(sgs[0])

    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    adam = admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["ABC"])
    traun = admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC"])

    seth.add_docs(num_docs_seth)  # ABC
    adam.add_docs(num_docs_adam, bulk=True)  # ABC
    traun.add_docs(num_docs_traun, bulk=True)  # ABC

    assert len(seth.cache) == num_docs_seth
    assert len(adam.cache) == num_docs_adam
    assert len(traun.cache) == num_docs_traun

    # discuss appropriate time with team
    time.sleep(10)

    # Each user should get all docs from all users
    all_caches = [seth.cache, adam.cache, traun.cache]
    all_docs = {k: v for cache in all_caches for k, v in cache.items()}

    verify_changes([seth, adam, traun], expected_num_docs=num_docs_seth + num_docs_adam + num_docs_traun, expected_num_updates=0, expected_docs=all_docs)




