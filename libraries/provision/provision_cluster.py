import os
import sys
from optparse import OptionParser

import install_sync_gateway
import install_couchbase_server

from clean_cluster import clean_cluster
from install_couchbase_server import CouchbaseServerConfig
from install_sync_gateway import SyncGatewayConfig
from install_nginx import install_nginx

from libraries.provision.install_deps import install_deps
from libraries.testkit.config import Config

from keywords.utils import log_info
from keywords.utils import version_and_build
from keywords.exceptions import ProvisioningError
from libraries.testkit.cluster import validate_cluster
from libraries.testkit.cluster import Cluster


def provision_cluster(cluster_config, couchbase_server_config, sync_gateway_config, sg_platform="centos", sa_platform="centos"):

    log_info("\n>>> Cluster info:\n")

    with open(cluster_config, "r") as ansible_hosts:
        log_info(ansible_hosts.read())

    log_info(couchbase_server_config)
    log_info(sync_gateway_config)

    if not sync_gateway_config.is_valid():
        log_info("Invalid sync_gateway provisioning configuration. Exiting ...")
        sys.exit(1)

    cluster = Cluster(config=cluster_config)
    config_path_full = os.path.abspath(sync_gateway_config.config_path)
    config = Config(config_path_full)

    is_valid, reason = validate_cluster(
        cluster.sync_gateways,
        cluster.sg_accels,
        config,
    )
    if not is_valid:
        raise ProvisioningError(reason)

    log_info(">>> Provisioning cluster...")

    # Get server base url and package name
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package()

    log_info(">>> Server package: {0}/{1}".format(server_baseurl, server_package_name))
    log_info(">>> Using sync_gateway config: {}".format(sync_gateway_config.config_path))

    # Reset previous installs
    clean_cluster(cluster_config)

    # Install server package
    log_info("Installing Couchbase Server")
    install_couchbase_server.install_couchbase_server(
        cluster_config=cluster_config,
        couchbase_server_config=couchbase_server_config
    )

    # Install sync_gateway
    log_info("Installing Sync Gateway")
    install_sync_gateway.install_sync_gateway(
        cluster_config=cluster_config,
        sync_gateway_config=sync_gateway_config,
        sg_platform=sg_platform,
        sa_platform=sa_platform
    )

    # Install nginx
    install_nginx(cluster_config)

    log_info(">>> Done provisioning cluster...")


if __name__ == "__main__":
    usage = """usage: python provision_cluster.py
    --server-version=<server_version_number>
    --sync-gateway-version=<sync_gateway_version_number>

    or

    usage: python provision_cluster.py
    --server-version=<server_version_number>
    --sync-gateway-commit=<sync_gateway_commit_to_build>
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

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
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

    provision_cluster(
        cluster_config=cluster_conf,
        couchbase_server_config=server_config,
        sync_gateway_config=sync_gateway_conf
    )
