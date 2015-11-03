import pytest

from cluster_setup import cluster

def test_1(cluster):

    cluster.reset()

    for sg in cluster.sync_gateways:
        print(sg.info())

    cluster.sync_gateways[0].restart("sync_gateway_config_test.json")





