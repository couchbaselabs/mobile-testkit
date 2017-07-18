import os

from libraries.provision.install_sync_gateway import SyncGatewayConfig
from keywords.utils import version_and_build


def test_ce_ee_package():
    sync_gateway_version = "1.5.0-477"
    cwd = os.getcwd()
    sync_gateway_config = cwd + "/resources/sync_gateway_configs/sync_gateway_default_cc.json"
    version, build = version_and_build(sync_gateway_version)

    sg_config = SyncGatewayConfig(
        commit=None,
        version_number=version,
        build_number=build,
        config_path=sync_gateway_config,
        build_flags="",
        skip_bucketcreation=False
    )

    sg_ce = True
    sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sg_config.sync_gateway_base_url_and_package(sg_ce)

    assert sync_gateway_package_name == "couchbase-sync-gateway-community_1.5.0-477_x86_64.rpm"
    assert sg_accel_package_name == "couchbase-sg-accel-community_1.5.0-477_x86_64.rpm"
    assert sync_gateway_base_url == "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.5.0/1.5.0-477"

    sg_ce = False
    sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sg_config.sync_gateway_base_url_and_package(sg_ce)

    assert sync_gateway_package_name == "couchbase-sync-gateway-enterprise_1.5.0-477_x86_64.rpm"
    assert sg_accel_package_name == "couchbase-sg-accel-enterprise_1.5.0-477_x86_64.rpm"
    assert sync_gateway_base_url == "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.5.0/1.5.0-477"
