import pytest
import json

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.views
@pytest.mark.role
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "user_views/user_views",
])
def test_user_views_sanity(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'single_user_multiple_channels'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_db = "db"

    topology = params_from_base_test_setup["cluster_topology"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_public_url = topology["sync_gateways"][0]["public"]

    client = MobileRestClient()

    # Issue GET /_user to exercise principal views
    users = client.get_users(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(users) == 2 and "seth" in users and "raghu" in users

    # Issue GET /_role to exercise principal views
    roles = client.get_roles(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(roles) == 2 and "Scientist" in roles and "Researcher" in roles

    design_doc = {
        "views": {
            "filtered": {
                "map": 'function(doc, meta) {emit(doc.name, null);}'
            }
        }
    }

    design_doc_id = client.add_design_doc(url=sg_admin_url, db=sg_db, name="test_views", doc=json.dumps(design_doc))

    import pdb
    pdb.set_trace()

