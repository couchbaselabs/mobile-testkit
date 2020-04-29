""" tests for runtime setting of cluster configuration """

import configparser
import json
import os

from utilities.cluster_config_utils import (is_cbs_ssl_enabled,
                                            is_xattrs_enabled,
                                            sg_ssl_enabled,
                                            persist_cluster_config_environment_prop)
from libraries.testkit.cluster import Cluster

MOCK_CLUSTER_CONFIG = os.getcwd() + "/mobile_testkit_tests/test_data/mock_base_di"
os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG + ".json"


def test_enable_cbs_ssl_in_cluster_config():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, 'sync_gateway_ssl', False)
    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.cbs_ssl

    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, 'cbs_ssl_enabled', True)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["cbs_ssl_enabled"]

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert c.cbs_ssl

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert config.getboolean('environment', 'cbs_ssl_enabled')


def test_enable_sg_ssl_in_cluster_config():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.sync_gateway_ssl

    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, 'sync_gateway_ssl', True)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["sync_gateway_ssl"]

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert c.sync_gateway_ssl

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert config.getboolean('environment', 'sync_gateway_ssl')


def test_is_cbs_ssl_enabled():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    enabled = is_cbs_ssl_enabled(MOCK_CLUSTER_CONFIG)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["cbs_ssl_enabled"] == enabled

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert config.getboolean('environment', 'cbs_ssl_enabled')


def test_is_sg_ssl_enabled():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    enabled = sg_ssl_enabled(MOCK_CLUSTER_CONFIG)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["sync_gateway_ssl"] == enabled

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert config.getboolean('environment', 'sync_gateway_ssl')


def test_disable_cbs_ssl_in_cluster_config():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, 'cbs_ssl_enabled', False)

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.cbs_ssl

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert not cluster_json["environment"]["cbs_ssl_enabled"]

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert not config.getboolean('environment', 'cbs_ssl_enabled')


def test_disable_sg_ssl_in_cluster_config():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, 'sync_gateway_ssl', False)

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.cbs_ssl

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert not cluster_json["environment"]["sync_gateway_ssl"]

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert not config.getboolean('environment', 'sync_gateway_ssl')


def test_is_cbs_ssl_disabled():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    disabled = is_cbs_ssl_enabled(MOCK_CLUSTER_CONFIG)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["sync_gateway_ssl"] == disabled

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert not config.getboolean("environment", "sync_gateway_ssl")


def test_is_sg_ssl_disabled():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    disabled = sg_ssl_enabled(MOCK_CLUSTER_CONFIG)

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    assert "environment" in cluster_json
    assert cluster_json["environment"]["cbs_ssl_enabled"] == disabled

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    assert config.has_section("environment")
    assert not config.getboolean("environment", "cbs_ssl_enabled")


def test_enable_disable_xattrs():
    os.environ["CLUSTER_CONFIG"] = MOCK_CLUSTER_CONFIG

    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.xattrs

    assert "environment" in cluster_json
    assert not cluster_json["environment"]["xattrs_enabled"]
    assert config.has_section("environment")
    assert not config.getboolean("environment", "xattrs_enabled")

    assert not is_xattrs_enabled(MOCK_CLUSTER_CONFIG)

    # Enable XATTRs
    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, "xattrs_enabled", True)

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert c.xattrs

    # Reload cluster config and ma
    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    # Make sure xattrs are enabled
    assert "environment" in cluster_json
    assert cluster_json["environment"]["xattrs_enabled"]
    assert config.has_section("environment")
    assert config.getboolean("environment", "xattrs_enabled")

    assert is_xattrs_enabled(MOCK_CLUSTER_CONFIG)

    # Disable XATTRs
    persist_cluster_config_environment_prop(MOCK_CLUSTER_CONFIG, "xattrs_enabled", False)

    c = Cluster(MOCK_CLUSTER_CONFIG)
    assert not c.xattrs

    # Reload cluster config and ma
    with open(MOCK_CLUSTER_CONFIG + ".json") as f:
        cluster_json = json.loads(f.read())

    config = configparser.ConfigParser()
    config.read(MOCK_CLUSTER_CONFIG)

    # Make sure xattrs are disabled
    assert "environment" in cluster_json
    assert not cluster_json["environment"]["xattrs_enabled"]
    assert config.has_section("environment")
    assert not config.getboolean("environment", "xattrs_enabled")

    assert not is_xattrs_enabled(MOCK_CLUSTER_CONFIG)
