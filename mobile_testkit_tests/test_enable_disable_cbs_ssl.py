import json
import os
import ConfigParser

from utilities.enable_disable_ssl_cluster import enable_cbs_ssl_in_cluster_config
from utilities.enable_disable_ssl_cluster import disable_cbs_ssl_in_cluster_config
from utilities.enable_disable_ssl_cluster import is_cbs_ssl_enabled

cwd = os.getcwd()
mock_cluster_config = cwd + "/mobile_testkit_tests/test_data/mock_base_di"


def test_enable_cbs_ssl_in_cluster_config():
    enable_cbs_ssl_in_cluster_config(mock_cluster_config)

    with open(mock_cluster_config + ".json") as f:
        cluster = json.loads(f.read())

    assert "cbs_ssl_enabled" in cluster and cluster["cbs_ssl_enabled"]

    config = ConfigParser.ConfigParser()
    config.read(mock_cluster_config)

    assert config.has_section("cbs_ssl") and config.get('cbs_ssl', 'cbs_ssl_enabled')


def test_is_cbs_ssl_enabled():
    enabled = is_cbs_ssl_enabled(mock_cluster_config)

    with open(mock_cluster_config + ".json") as f:
        cluster = json.loads(f.read())

    assert "cbs_ssl_enabled" in cluster and cluster["cbs_ssl_enabled"] == enabled

    config = ConfigParser.ConfigParser()
    config.read(mock_cluster_config)

    assert config.has_section("cbs_ssl") and config.get('cbs_ssl', 'cbs_ssl_enabled')


def test_disable_cbs_ssl_in_cluster_config():
    disable_cbs_ssl_in_cluster_config(mock_cluster_config)

    with open(mock_cluster_config + ".json") as f:
        cluster = json.loads(f.read())

    assert "cbs_ssl_enabled" in cluster and not cluster["cbs_ssl_enabled"]

    config = ConfigParser.ConfigParser()
    config.read(mock_cluster_config)

    assert config.has_section("cbs_ssl") and config.get('cbs_ssl', 'cbs_ssl_enabled') == 'False'


def test_is_cbs_ssl_disabled():
    disabled = is_cbs_ssl_enabled(mock_cluster_config)

    with open(mock_cluster_config + ".json") as f:
        cluster = json.loads(f.read())

    assert "cbs_ssl_enabled" in cluster and cluster["cbs_ssl_enabled"] == disabled

    config = ConfigParser.ConfigParser()
    config.read(mock_cluster_config)

    assert config.has_section("cbs_ssl") and config.get('cbs_ssl', 'cbs_ssl_enabled') == 'False'
