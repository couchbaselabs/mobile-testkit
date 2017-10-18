import os
import pytest

from libraries.provision.install_sync_gateway import SyncGatewayConfig
from keywords.utils import version_and_build


@pytest.mark.parametrize("sg_ce, sg_type", [
    (True, "community"),
    (False, "enterprise"),
])
def test_ce_ee_package(sg_ce, sg_type):
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

    sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sg_config.sync_gateway_base_url_and_package(sg_ce)

    assert sync_gateway_package_name == "couchbase-sync-gateway-{}_1.5.0-477_x86_64.rpm".format(sg_type)
    assert sg_accel_package_name == "couchbase-sg-accel-enterprise_1.5.0-477_x86_64.rpm"
    assert sync_gateway_base_url == "http://latestbuilds.service.couchbase.com/builds/latestbuilds/sync_gateway/1.5.0/477"
