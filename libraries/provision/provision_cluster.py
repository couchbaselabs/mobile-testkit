import os
import os.path
import sys
from optparse import OptionParser

import libraries.provision.install_sync_gateway as install_sync_gateway
import libraries.provision.install_couchbase_server as install_couchbase_server
from libraries.provision.clean_cluster import clean_cluster
from libraries.provision.install_couchbase_server import CouchbaseServerConfig
from libraries.provision.install_sync_gateway import SyncGatewayConfig
from libraries.provision.install_nginx import install_nginx
from libraries.provision.install_deps import install_deps
from libraries.testkit.config import Config
from keywords.utils import log_info
from keywords.utils import version_and_build
from keywords.exceptions import ProvisioningError
from libraries.testkit.cluster import validate_cluster
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, is_cbs_ssl_enabled
from keywords.couchbaseserver import CouchbaseServer
from keywords.ClusterKeywords import ClusterKeywords
from utilities.cluster_config_utils import get_load_balancer_ip


def provision_cluster(cluster_config, couchbase_server_config, sync_gateway_config, sg_ssl=False, sg_lb=False, cbs_ssl=False, use_views=False,
                      xattrs_enabled=False, no_conflicts_enabled=False, delta_sync_enabled=False, number_replicas=0, sg_ce=False,
                      cbs_platform="centos7", sg_platform="centos", sg_installer_type="msi", sa_platform="centos",
                      sa_installer_type="msi", cbs_ce=False, aws=False, skip_couchbase_provision=False):

    if is_cbs_ssl_enabled(cluster_config):
        log_info("WARNING: Potentially overwriting the user flag server_tls_skip_verify to True because the server is using ssl")
        persist_cluster_config_environment_prop(cluster_config, 'server_tls_skip_verify', True)
        log_info("WARNING: Potentially overwriting the user flag disable_tls_server to False because the server is using ssl")
        persist_cluster_config_environment_prop(cluster_config, 'disable_tls_server', False)

    log_info("\n>>> Cluster info:\n")
    server_version = "{}-{}".format(couchbase_server_config.version, couchbase_server_config.build)
    sg_version = "{}-{}".format(sync_gateway_config._version_number, sync_gateway_config._build_number)

    try:
        server_version
    except NameError:
        log_info("Server version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'server_version', "")
    else:
        log_info("Running test with server version {}".format(server_version))
        persist_cluster_config_environment_prop(cluster_config, 'server_version', server_version)

    try:
        sg_version
    except NameError:
        log_info("Sync gateway version is not provided")
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', "")
    else:
        log_info("Running test with sync_gateway version {}".format(sg_version))
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_version', sg_version)

    with open(cluster_config, "r") as ansible_hosts:
        log_info(ansible_hosts.read())

    log_info(couchbase_server_config)
    log_info(sync_gateway_config)
    if not sync_gateway_config.is_valid():
        log_info("Invalid sync_gateway provisioning configuration. Exiting ...")
        sys.exit(1)

    cluster = Cluster(config=cluster_config)
    config_path_full = os.path.abspath(sync_gateway_config.config_path)
    config = Config(config_path_full, cluster_config)

    is_valid, reason = validate_cluster(
        cluster.sync_gateways,
        cluster.sg_accels,
        config,
    )
    if not is_valid:
        raise ProvisioningError(reason)

    log_info(">>> Provisioning cluster...", cluster_config)

    # Get server base url and package name
    cluster_keywords = ClusterKeywords(cluster_config)
    cluster_topology = cluster_keywords.get_cluster_topology(cluster_config)
    server_url = cluster_topology["couchbase_servers"][0]
    cb_server = CouchbaseServer(server_url)
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package(cb_server, cbs_platform, cbs_ce)

    log_info(">>> Server package: {0}/{1}".format(server_baseurl, server_package_name))
    log_info(">>> Using sync_gateway config: {}".format(sync_gateway_config.config_path))

    # Reset previous installs
    clean_cluster(cluster_config, skip_couchbase_provision=skip_couchbase_provision)

    if not skip_couchbase_provision:
        # Install server package
        log_info("Installing Couchbase Server")
        install_couchbase_server.install_couchbase_server(
            cluster_config=cluster_config,
            couchbase_server_config=couchbase_server_config,
            cbs_platform=cbs_platform, cbs_ce=cbs_ce
        )

    # Install sync_gateway
    log_info("Installing Sync Gateway")
    install_sync_gateway.install_sync_gateway(
        cluster_config=cluster_config,
        sg_installer_type=sg_installer_type,
        sync_gateway_config=sync_gateway_config,
        sg_platform=sg_platform,
        sa_platform=sa_platform,
        sa_installer_type=sa_installer_type,
        sg_ce=sg_ce,
        ipv6=cluster.ipv6,
        aws=aws
    )

    # Install nginx
    install_nginx(cluster_config)

    log_info(">>> Done provisioning cluster...")


def provision_cluster_aws(cluster_config, couchbase_server_config, sync_gateway_config, sg_ssl=False, sg_lb=False, cbs_ssl=False, use_views=False,
                          xattrs_enabled=False, no_conflicts_enabled=False, delta_sync_enabled=False, number_replicas=0, sg_ce=False,
                          cbs_platform="centos7", sg_platform="centos", sg_installer_type="msi", sa_platform="centos",
                          sa_installer_type="msi", cbs_ce=False, aws=False, skip_couchbase_provision=False, enable_cbs_developer_preview=False, disable_persistent_config=False):

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

    if cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled")
        # Enable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)
    else:
        log_info("Running tests with cbs <-> sg ssl disabled")
        # Disable ssl in cluster configs
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', False)

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

    if xattrs_enabled:
        log_info("Running test with xattrs for sync meta storage")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
    else:
        log_info("Using document storage for sync meta data")
        persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

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

    provision_cluster(cluster_config=cluster_conf, couchbase_server_config=server_config,
                      sync_gateway_config=sync_gateway_conf, cbs_platform=opts.cbs_platform, aws=aws)


if __name__ == "__main__":
    usage = """usage: python provision_cluster.py
    --server-version=<server_version_number>
    --sync-gateway-version=<sync_gateway_version_number>
    --xattrs=<True/False>
    --delta-sync=<True/False>
    --server-ssl=<True/False>

    or

    usage: python provision_cluster.py
    --server-version=<server_version_number>
    --sync-gateway-commit=<sync_gateway_commit_to_build>
    --xattrs=<True/False>
    --delta-sync=<True/False>
    --server-ssl=<True/False>
    """
    parser = OptionParser(usage=usage)

    default_sync_gateway_config = os.path.abspath("resources/sync_gateway_configs/sync_gateway_default_di.json")

    parser.add_option("", "--server-version",
                      action="store", type="string", dest="server_version", default=None,
                      help="server version to download")

    parser.add_option("", "--sync-gateway-version",
                      action="store", type="string", dest="sync_gateway_version", default=None,
                      help="sync_gateway release version to download (ex. 1.2.0-5)")

    parser.add_option("", "--sync-gateway-config-file",
                      action="store",
                      type="string",
                      dest="sync_gateway_config_file",
                      default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file, uses" +
                           " 'resources/sync_gateway_configs/sync_gateway_default_di.json' by default")

    parser.add_option("", "--sync-gateway-commit",
                      action="store", type="string", dest="source_commit", default=None,
                      help="sync_gateway branch to checkout and build")

    parser.add_option("", "--build-flags",
                      action="store", type="string", dest="build_flags", default="",
                      help="build flags to pass when building sync gateway (ex. -race)")

    parser.add_option("", "--install-deps",
                      action="store_true", dest="install_deps_flag", default=False,
                      help="Install dependent 3rd party packages")

    parser.add_option("", "--cbs-platform",
                      action="store", type="string", dest="cbs_platform", default="centos7",
                      help="Server Platfrom to download and install. Ex: centos7/centos6")

    parser.add_option("", "--xattrs",
                      action="store", type="string", dest="xattrs_enabled", default=False,
                      help="Use xattrs for sync meta storage. Only works with Sync Gateway 1.5.0+ and Couchbase Server 5.0+")

    parser.add_option("", "--server-ssl",
                      action="store", type="string", dest="cbs_ssl", default=False,
                      help="If set, will enable SSL communication between server and Sync Gateway")

    parser.add_option("", "--sg-lb",
                      action="store", type="string", dest="sg_lb", default=False,
                      help="If set, will enable load balancer for Sync Gateway")

    parser.add_option("", "--no-conflicts",
                      action="store", type="string", dest="no_conflicts_enabled", default=False,
                      help="If set, allow_conflicts is set to false in sync-gateway config")

    parser.add_option("--sg-ssl",
                      action="store", type="string", dest="sg_ssl", default=False,
                      help="If set, will enable SSL communication between Sync Gateway and CBL")

    parser.add_option("", "--use-views",
                      action="store", type="string", dest="use_views", default=False,
                      help="If set, uses views instead of GSI - SG 2.1 and above only")

    parser.add_option("", "--number-replicas",
                      action="store", type="int", dest="number_replicas", default=0,
                      help="Number of replicas for the indexer node - SG 2.1 and above only")

    parser.add_option("", "--delta-sync",
                      action="store", type="string", dest="delta_sync_enabled", default=False,
                      help="delta-sync: Enable delta-sync for sync gateway")

    parser.add_option("", "--enable-cbs-developer-preview",
                      action="store", type="string", dest="enable_cbs_dp",
                      help="Enabling CBS developer preview",
                      default=False)
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    server_config = CouchbaseServerConfig(
        version=opts.server_version
    )

    sync_gateway_version = None
    sync_gateway_build = None

    if opts.sync_gateway_version is not None:
        sync_gateway_version, sync_gateway_build = version_and_build(opts.sync_gateway_version)

    if opts.install_deps_flag:
        install_deps(cluster_conf)

    sync_gateway_conf = SyncGatewayConfig(
        version_number=sync_gateway_version,
        build_number=sync_gateway_build,
        commit=opts.source_commit,
        build_flags=opts.build_flags,
        config_path=opts.sync_gateway_config_file,
        skip_bucketcreation=False
    )

    provision_cluster_aws(
        sg_ssl=opts.sg_ssl, sg_lb=opts.sg_lb, cbs_ssl=opts.cbs_ssl, use_views=opts.use_views, xattrs_enabled=opts.xattrs_enabled, no_conflicts_enabled=opts.no_conflicts_enabled,
        delta_sync_enabled=opts.delta_sync_enabled, number_replicas=opts.number_replicas, cluster_config=cluster_conf, couchbase_server_config=server_config,
        sync_gateway_config=sync_gateway_conf, cbs_platform=opts.cbs_platform, aws=True, enable_cbs_developer_preview=opts.enable_cbs_dp
    )
