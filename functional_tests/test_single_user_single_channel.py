import time
from lib.admin import Admin
import pytest

from lib.verify import verify_changes

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.sanity
def test_single_user_single_channel(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    sgs = cluster.sync_gateways

    # TODO Parametrize
    num_seth_docs = 70
    num_admin_docs = 30

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin_user = admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    seth.add_docs(num_seth_docs)
    admin_user.add_docs(num_admin_docs)

    assert len(seth.cache) == num_seth_docs
    assert len(admin_user.cache) == num_admin_docs

    time.sleep(10)

    seth_pushed_doc_ids = seth.cache.keys()
    verify_changes([seth], expected_num_docs=num_seth_docs, expected_num_updates=0, expected_docs=seth.cache)

    all_doc_caches = [seth.cache, admin_user.cache]
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}
    verify_changes([admin_user], expected_num_docs=num_seth_docs + num_admin_docs, expected_num_updates=0, expected_docs=all_docs)


