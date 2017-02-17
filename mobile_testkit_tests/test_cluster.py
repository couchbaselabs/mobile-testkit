
from libraries.testkit.cluster import validate_cluster
from libraries.testkit.config import Config

import pytest

from utilities import scan_logs


def test_validate_cluster():
    """
    Make sure validate cluster catches invalid clusters
    """
    sync_gateways = ["sg1"]
    sg_accels = []
    config = Config(conf_path=None)
    config.mode = "di"

    is_valid, _ = validate_cluster(sync_gateways, sg_accels, config)
    assert is_valid == False

    sg_accels.append("sga1")
    is_valid, _ = validate_cluster(sync_gateways, sg_accels, config)
    assert is_valid == True
