import pytest

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info

from libraries.testkit.cluster import Cluster


@pytest.mark.sdk
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.basicauth
@pytest.mark.access
@pytest.mark.channel
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_sdk_interop_unique_docs(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology["sync_gateways"][0]["admin"]
    sg_url = cluster_topology["sync_gateways"][0]["public"]
    bucket = "data-bucket"

    cbs_url = cluster_topology["couchbase_servers"][0]

    log_info("sg_conf: {}".format(sg_conf))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("sg_url: {}".format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    



