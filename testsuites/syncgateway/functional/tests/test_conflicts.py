import pytest
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit import cluster
from keywords.MobileRestClient import MobileRestClient
from keywords import userinfo


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests"
])
def test_non_winning_revisions(params_from_base_test_setup, sg_conf_name):

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    client = MobileRestClient()

