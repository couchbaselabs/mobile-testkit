import pytest

import keywords.utils
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

def grant_access(access_type, user, channel):
    pass


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.parametrize("sg_conf_name, grant_type", [
    ("sync_gateway_default", "grant_type")
])
def test_backfill_scenario_one(params_from_base_test_setup, sg_conf_name, grant_type):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    topology = params_from_base_test_setup["topology"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    #user_b = client.create_user(url=sg_admin_url)

