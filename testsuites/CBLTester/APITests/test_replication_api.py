import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import CLUSTER_CONFIGS_DIR
from libraries.testkit import cluster

@pytest.mark.sanity
@pytest.mark.listener
def test_replication_configuration_invalid_db(params_from_base_test_setup):
    """
        @summary: 
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication with empty string of source db
        3. Verify that it throws http error bad request
        4. Configure replication with source db None
        5. Verify that it throws invalid type of db
        6. Configure replication with empty target url
        7. Verify that it throws http error bad request
        8. Configure replication with target url None
        9. Verify that it throws invalid type
        10. Configure replication with empty target db
        11. Verify that it throws http error bad request
        12. Configure replication with target db None
        13. Verify that it throws invalid type
    """
    cbl_db_name = "cbl_db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = sg_admin_url.replace("http", "blip")
    sg_blip_url = "{}/db".format(sg_blip_url)
    channels = ["ABC"]
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    db = Database(base_url)

    # Create CBL database
    db_config = db.configure()
    cbl_db = db.create(cbl_db_name, db_config)

    # Reset cluster to ensure no data in system
    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    db.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
    replicator = Replication(base_url)
    # Test for empty string for source db
    with pytest.raises(HTTPError) as he:
        replicator.configure("", target_url=sg_blip_url, continuous=True)
    assert he.value.message.startswith('400 Client Error: Bad Request for url:'), "Did not caught http error when source db passed as empty string"
    # Test for source db with none value
    with pytest.raises(Exception) as he:
        replicator.configure(None, target_url=sg_blip_url, continuous=True)
    assert he.value.message.startswith('Invalid value type: None'), "Did not caught http error when source db is none"

    # Test for empty string for target url
    with pytest.raises(HTTPError) as he:
        replicator.configure(cbl_db, target_url="", continuous=True)
    assert he.value.message.startswith('400 Client Error: Bad Request for url:'), "Did not caught http error when source db passed as empty string"
    # Test for target url with none value
    with pytest.raises(Exception) as he:
        replicator.configure(cbl_db, target_url=None, continuous=True)
    assert he.value.message.startswith('Invalid value type: None'), "Did not caught http error when source db is none"

    # Test for empty string for target DB
    with pytest.raises(HTTPError) as he:
        replicator.configure(cbl_db, target_db="", continuous=True)
    assert he.value.message.startswith('400 Client Error: Bad Request for url:'), "Did not caught http error when source db passed as empty string"
    # Test for target url with none value
    with pytest.raises(Exception) as he:
        replicator.configure(cbl_db, target_db=None, continuous=True)
    assert he.value.message.startswith('Invalid value type: None'), "Did not caught http error when source db is none"
