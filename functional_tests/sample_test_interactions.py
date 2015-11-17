import pytest

from fixtures import cluster

def test_1(cluster):

    cluster.reset("sync_gateway_default_functional_tests.json")

    for sg in cluster.sync_gateways:
        print(sg.info())

    print("STOPPING")
    cluster.sync_gateways[1].stop()
    print("STARTING")
    cluster.sync_gateways[1].start("sync_gateway_default.json")

    cluster.sync_gateways[0].restart("sync_gateway_config_test.json")

    cluster.servers[0].create_buckets(["data-bucket-1", "data-bucket-2", "index-bucket-1", "index-bucket-2"])





