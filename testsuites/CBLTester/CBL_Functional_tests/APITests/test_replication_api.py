import pytest

from CBLClient.Database import Database
from CBLClient.Replication import Replication
from requests.exceptions import HTTPError
from keywords.SyncGateway import sync_gateway_config_path_for_mode
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
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    channels = ["ABC"]
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)

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
