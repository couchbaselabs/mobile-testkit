import time

import pytest
import concurrent.futures

from lib.admin import Admin

from fixtures import cluster

@pytest.mark.extendedsanity
def test_dcp_reshard(cluster):

    cluster.reset("sync_gateway_default_functional_tests.json")

    # Reset with the same config, except the num_shards has changed
    restart_status = cluster.sync_gateways[0].restart("sync_gateway_functional_tests_32_shard.json")

    # Assert that the sync_gateway fails to launch
    assert restart_status != 0
