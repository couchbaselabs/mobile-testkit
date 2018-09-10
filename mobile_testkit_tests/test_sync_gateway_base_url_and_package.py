import os
import pytest

from libraries.provision.install_sync_gateway import SyncGatewayConfig
from keywords.utils import version_and_build


@pytest.mark.parametrize("sg_ce, sg_type, sg_platform, sa_platform, platform_ext, sg_installer_type", [
    (True, "community", "centos", "centos", "rpm", None),
    (False, "enterprise", "windows", "windows", "exe", "exe"),
    (False, "enterprise", "windows", "windows", "msi", "msi"),
])
def test_ce_ee_package(sg_ce, sg_type, sg_platform, sa_platform, platform_ext, sg_installer_type):
    sync_gateway_version = "2.1.0-138"
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

    sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sg_config.sync_gateway_base_url_and_package(sg_ce=sg_ce, sg_platform=sg_platform, sa_platform=sa_platform, sg_installer_type=sg_installer_type)

    assert sync_gateway_package_name == "couchbase-sync-gateway-{}_2.1.0-138_x86_64.{}".format(sg_type, platform_ext)
    assert sg_accel_package_name == "couchbase-sg-accel-{}_2.1.0-138_x86_64.{}".format(sg_type, platform_ext)
    assert sync_gateway_base_url == "http://latestbuilds.service.couchbase.com/builds/latestbuilds/sync_gateway/2.1.0/138"
