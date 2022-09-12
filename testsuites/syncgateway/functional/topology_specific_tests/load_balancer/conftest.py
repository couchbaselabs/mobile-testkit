import pytest

import keywords.constants
from keywords.ClusterKeywords import ClusterKeywords
from keywords.exceptions import ProvisioningError, FeatureSupportedError
from keywords.SyncGateway import (sync_gateway_config_path_for_mode,
                                  validate_sync_gateway_mode)
from keywords.tklogging import Logging
from keywords.utils import check_xattr_support, log_info, version_is_binary, clear_resources_pngs
from libraries.NetworkUtils import NetworkUtils
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop
from utilities.cluster_config_utils import get_load_balancer_ip


# This will be called once at the beggining of the execution in the 'tests/load_balancer' directory
# and will be torn down, (code after the yeild) after each .py file in this directory
@pytest.fixture(scope="module")
def params_from_base_suite_setup(request):
    log_info("Setting up 'params_from_base_suite_setup' ...")

    # pytest command line parameters
    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")
    disable_tls_server = request.config.getoption("--disable-tls-server")
    mode = request.config.getoption("--mode")
    skip_provisioning = request.config.getoption("--skip-provisioning")
    race_enabled = request.config.getoption("--race")
    cbs_ssl = request.config.getoption("--server-ssl")
    xattrs_enabled = request.config.getoption("--xattrs")
    sg_lb = request.config.getoption("--sg-lb")
    sg_ce = request.config.getoption("--sg-ce")
    cbs_ce = request.config.getoption("--cbs-ce")
    use_sequoia = request.config.getoption("--sequoia")
    no_conflicts_enabled = request.config.getoption("--no-conflicts")
    sg_ssl = request.config.getoption("--sg-ssl")
    use_views = request.config.getoption("--use-views")
    number_replicas = request.config.getoption("--number-replicas")
    sg_installer_type = request.config.getoption("--sg-installer-type")
    sa_installer_type = request.config.getoption("--sa-installer-type")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    sg_platform = request.config.getoption("--sg-platform")
    cbs_platform = request.config.getoption("--cbs-platform")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    cbs_platform = request.config.getoption("--cbs-platform")
    magma_storage_enabled = request.config.getoption("--magma-storage")
    hide_product_version = request.config.getoption("--hide-product-version")
    prometheus_enabled = request.config.getoption("--prometheus-enable")
    skip_couchbase_provision = request.config.getoption("--skip-couchbase-provision")
    enable_cbs_developer_preview = request.config.getoption("--enable-cbs-developer-preview")
    disable_persistent_config = request.config.getoption("--disable-persistent-config")
    enable_server_tls_skip_verify = request.config.getoption("--enable-server-tls-skip-verify")
    disable_tls_server = request.config.getoption("--disable-tls-server")
    disable_admin_auth = request.config.getoption("--disable-admin-auth")

    if xattrs_enabled and version_is_binary(sync_gateway_version):
        check_xattr_support(server_version, sync_gateway_version)

    if delta_sync_enabled and sync_gateway_version < "2.5":
        raise FeatureSupportedError('Delta sync feature not available for sync-gateway version below 2.5, so skipping the test')

    log_info("server_version: {}".format(server_version))
    log_info("sync_gateway_version: {}".format(sync_gateway_version))
    log_info("mode: {}".format(mode))
    log_info("skip_provisioning: {}".format(skip_provisioning))
    log_info("race_enabled: {}".format(race_enabled))
    log_info("cbs_ssl: {}".format(cbs_ssl))
    log_info("xattrs_enabled: {}".format(xattrs_enabled))
    log_info("sg_lb: {}".format(sg_lb))
    log_info("sg_ce: {}".format(sg_ce))
    log_info("sg_ssl: {}".format(sg_ssl))
    log_info("no conflicts enabled {}".format(no_conflicts_enabled))
    log_info("use_views: {}".format(use_views))
    log_info("number_replicas: {}".format(number_replicas))
    log_info("sg_installer_type: {}".format(sg_installer_type))
    log_info("sa_installer_type: {}".format(sa_installer_type))
    log_info("delta_sync_enabled: {}".format(delta_sync_enabled))
    log_info("sg_platform: {}".format(sg_platform))
    log_info("cbs_platform: {}".format(cbs_platform))
    log_info("Delta_sync: {}".format(delta_sync_enabled))
    log_info("prometheus_enabled: {}".format(prometheus_enabled))
    log_info("enable_cbs_developer_preview: {}".format(enable_cbs_developer_preview))
    log_info("disable_persistent_config: {}".format(disable_persistent_config))

    # sg-ce is invalid for di mode
    if mode == "di" and sg_ce:
        raise FeatureSupportedError("SGAccel is only available as an enterprise edition")

    if no_conflicts_enabled and sync_gateway_version < "2.0":
        raise FeatureSupportedError('No conflicts feature not available for sync-gateway version below 2.0, so skipping the test')

    # Make sure mode for sync_gateway is supported ('cc' or 'di')
    validate_sync_gateway_mode(mode)

    # use load_balancer_cc cluster config if mode is "cc" or load_balancer_di cluster config if mode is "di"
    cluster_config = "{}/load_balancer_{}".format(keywords.constants.CLUSTER_CONFIGS_DIR, mode)
    cluster_utils = ClusterKeywords(cluster_config)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_default_functional_tests", mode)

    if sg_ssl:
        log_info("Enabling SSL on sync gateway")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)
    else:
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', False)

    # Add load balancer prop and check if load balancer IP is available
    if sg_lb:
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', True)
        log_info("Running tests with load balancer enabled: {}".format(get_load_balancer_ip(cluster_config)))
    else:
        log_info("Running tests with load balancer disabled")
        persist_cluster_config_environment_prop(cluster_config, 'sg_lb_enabled', False)

    if use_views:
        log_info("Running SG tests using views")
        # Enable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable sg views in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', False)

    # Write the number of replicas to cluster config
    persist_cluster_config_environment_prop(cluster_config, 'number_replicas', number_replicas)

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

    if xattrs_enabled:
        log_info("Running test with xattrs for sync meta storage")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
    else:
        log_info("Using document storage for sync meta data")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

    try:
        server_version
    except NameError:
        log_info("Server version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'server_version', "")
    else:
        log_info("Running test with server version {}".format(server_version))
        persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)

    try:
        sync_gateway_version
    except NameError:
        log_info("Sync gateway version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', "")
    else:
        log_info("Running test with sync_gateway version {}".format(sync_gateway_version))
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sync_gateway_version)

    try:
        sg_platform
    except NameError:
        log_info("sg platform  is not provided, so by default it runs on Centos")
        persist_cluster_config_environment_prop(cluster_config, 'sg_platform', "centos", False)
    else:
        log_info("Running test with sg platform {}".format(sg_platform))
        persist_cluster_config_environment_prop(cluster_config, 'sg_platform', sg_platform, False)

    try:
        cbs_platform
    except NameError:
        log_info("cbs platform  is not provided, so by default it runs on Centos")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_platform', "centos7", False)
    else:
        log_info("Running test with sg platform {}".format(cbs_platform))
        persist_cluster_config_environment_prop(cluster_config, 'cbs_platform', cbs_platform, False)

    if no_conflicts_enabled:
        log_info("Running with no conflicts")
        persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', True)
    else:
        log_info("Running with allow conflicts")
        persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', False)

    if delta_sync_enabled:
        log_info("Running with delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
    else:
        log_info("Running without delta sync")
        persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    try:
        cbs_platform
    except NameError:
        log_info("cbs platform  is not provided, so by default it runs on Centos7")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_platform', "centos7", False)
    else:
        log_info("Running test with cbs platform {}".format(cbs_platform))
        persist_cluster_config_environment_prop(cluster_config, 'cbs_platform', cbs_platform, False)

    if magma_storage_enabled:
        log_info("Running with magma storage")
        persist_cluster_config_environment_prop(cluster_config, 'magma_storage_enabled', True, False)
    else:
        log_info("Running without magma storage")
        persist_cluster_config_environment_prop(cluster_config, 'magma_storage_enabled', False, False)

    if hide_product_version:
        log_info("Suppress the SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', True)
    else:
        log_info("Running without suppress SGW product Version")
        persist_cluster_config_environment_prop(cluster_config, 'hide_product_version', False)

    if enable_cbs_developer_preview:
        log_info("Enable CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', True)
    else:
        log_info("Running without CBS developer preview")
        persist_cluster_config_environment_prop(cluster_config, 'cbs_developer_preview', False)

    if disable_persistent_config:
        log_info(" disable persistent config")
        persist_cluster_config_environment_prop(cluster_config, 'disable_persistent_config', True)
    else:
        log_info("Running without Centralized Persistent Config")
        persist_cluster_config_environment_prop(cluster_config, 'disable_persistent_config', False)

    if enable_server_tls_skip_verify:
        log_info("Enable server tls skip verify flag")
        persist_cluster_config_environment_prop(cluster_config, 'server_tls_skip_verify', True)
    else:
        log_info("Running without server_tls_skip_verify Config")
        persist_cluster_config_environment_prop(cluster_config, 'server_tls_skip_verify', False)

    if disable_tls_server:
        if cbs_ssl is False:
            log_info("Disable tls server flag")
            persist_cluster_config_environment_prop(cluster_config, 'disable_tls_server', True)
        else:
            log_info("Enable tls server flag")
            persist_cluster_config_environment_prop(cluster_config, 'disable_tls_server', False)

    if disable_admin_auth:
        log_info("Disabled Admin Auth")
        persist_cluster_config_environment_prop(cluster_config, 'disable_admin_auth', True)
    else:
        log_info("Enabled Admin Auth")
        persist_cluster_config_environment_prop(cluster_config, 'disable_admin_auth', False)

    if sync_gateway_version < "2.0.0" and no_conflicts_enabled:
        pytest.skip("Test cannot run with no-conflicts with sg version < 2.0.0")

    # Skip provisioning if user specifies '--skip-provisoning' or '--sequoia'
    should_provision = True
    if skip_provisioning or use_sequoia:
        should_provision = False

    cluster_utils = ClusterKeywords(cluster_config)
    if should_provision:
        try:
            cluster_utils.provision_cluster(
                cluster_config=cluster_config,
                server_version=server_version,
                sync_gateway_version=sync_gateway_version,
                sync_gateway_config=sg_config,
                race_enabled=race_enabled,
                cbs_platform=cbs_platform,
                sg_ce=sg_ce,
                cbs_ce=cbs_ce,
                sg_platform=sg_platform,
                sg_installer_type=sg_installer_type,
                sa_installer_type=sa_installer_type,
                skip_couchbase_provision=skip_couchbase_provision
            )
        except ProvisioningError:
            logging_helper = Logging()
            logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=request.node.name)
            raise

    # Hit this intalled running services to verify the correct versions are installed
    cluster_utils.verify_cluster_versions(
        cluster_config,
        expected_server_version=server_version,
        expected_sync_gateway_version=sync_gateway_version
    )
    need_sgw_admin_auth = (not disable_admin_auth) and sync_gateway_version >= "3.0"

    yield {"cluster_config": cluster_config, "mode": mode, "sg_platform": sg_platform, "sg_ce": sg_ce, "need_sgw_admin_auth": need_sgw_admin_auth}

    log_info("Tearing down 'params_from_base_suite_setup' ...")

    # Stop all sync_gateway and sg_accels as test finished
    c = cluster.Cluster(cluster_config)
    c.stop_sg_and_accel()

    # Delete png files under resources/data
    clear_resources_pngs()


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):

    # pytest command line parameters
    collect_logs = request.config.getoption("--collect-logs")

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    cluster_config = params_from_base_suite_setup["cluster_config"]
    mode = params_from_base_suite_setup["mode"]
    sg_platform = params_from_base_suite_setup["sg_platform"]
    sg_ce = params_from_base_suite_setup["sg_ce"]
    need_sgw_admin_auth = params_from_base_suite_setup["need_sgw_admin_auth"]

    yield {
        "cluster_config": cluster_config,
        "mode": mode,
        "sg_platform": sg_platform,
        "sg_ce": sg_ce,
        "need_sgw_admin_auth": need_sgw_admin_auth
    }

    log_info("Tearing down test '{}'".format(test_name))

    # Capture testkit socket usage
    network_utils = NetworkUtils()
    network_utils.list_connections()

    # Verify all sync_gateways and sg_accels are reachable
    c = cluster.Cluster(cluster_config)
    errors = c.verify_alive(mode)

    # if the test failed pull logs
    if collect_logs or request.node.rep_call.failed or len(errors) != 0:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=cluster_config, test_name=test_name)
