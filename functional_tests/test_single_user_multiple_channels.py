import time

import pytest

from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.sanity
def test_single_user_multiple_channels(cluster):

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

    print(seth)

    time.sleep(10)

    verify_changes(users=[seth], expected_num_docs=2000, expected_num_updates=0, expected_docs=seth.cache)

    end = time.time()
    print("TIME:{}s".format(end - start))

