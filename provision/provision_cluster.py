import os
import sys
from optparse import OptionParser

import install_sync_gateway
import install_couchbase_server

from install_couchbase_server import CouchbaseServerConfig
from install_sync_gateway import SyncGatewayConfig

import ansible_runner

# TODO Add SG package

def provision_cluster(couchbase_server_config, sync_gateway_config, install_deps):

    print "\n>>> Host info:\n"

    with open("provisioning_config", "r") as ansible_hosts:
        print(ansible_hosts.read())

    print(couchbase_server_config)
    print(sync_gateway_config)

    print(">>> Validating...")

    if not couchbase_server_config.is_valid():
        print("Invalid server provisioning configuration. Exiting ...")
        sys.exit(1)

    if not sync_gateway_config.is_valid():
        print("Invalid sync_gateway provisioning configuration. Exiting ...")
        sys.exit(1)

    print(">>> Provisioning cluster...")

    # Get server base url and package name
    server_base_url, server_package_name = couchbase_server_config.server_base_url_and_package()

    print(">>> Server package: {0}/{1}".format(server_base_url, server_package_name))

    if sync_gateway_config.branch is not None:
        print(">>> Building sync_gateway: branch={}".format(sync_gateway_config.branch))
    else:
        # TODO
        print(">>> sync_gateway package")

    print(">>> Using sync_gateway config: {}".format(sync_gateway_config.config_path))

    # Reset previous installs
    ansible_runner.run_ansible_playbook("remove-previous-installs.yml")

    if install_deps:
        # OS-level modifications
        ansible_runner.run_ansible_playbook("os-level-modifications.yml")

        # Install dependencies
        ansible_runner.run_ansible_playbook("install-common-tools.yml")

    # Install server package
    install_couchbase_server.install_couchbase_server(couchbase_server_config)

    # Install sync_gateway
    install_sync_gateway.install_sync_gateway(sync_gateway_config)

if __name__ == "__main__":
    usage = """usage: python provision_cluster.py
    --server-version=<server_version_number>
    --server-build=<server_build_number>
    --sync-gateway-version=<sync_gateway_version_number>
    --sync-gateway-build=<sync_gateway_build_number>

    or

    usage: python provision_cluster.py
    --server-version=<server_version_number>
    --server-build=<server_build_number>
    --branch=<sync_gateway_branch_to_build>
    """

    parser = OptionParser(usage=usage)

    default_sync_gateway_config = os.path.abspath("conf/sync_gateway_default.json")

    parser.add_option("", "--server-version",
                      action="store", type="string", dest="server_version", default=None,
                      help="server version to download")

    parser.add_option("", "--sync-gateway-version",
                      action="store", type="string", dest="sync_gateway_version", default=None,
                      help="sync_gateway release version to download (ex. 1.2.0-5)")

    parser.add_option("", "--sync-gateway-dev-build-url",
                      action="store", type="string", dest="sync_gateway_dev_build_url", default=None,
                      help="sync_gateway dev build url to download (eg, feature/distributed_index)")

    parser.add_option("", "--sync-gateway-dev-build-number",
                      action="store", type="string", dest="sync_gateway_dev_build_number", default=None,
                      help="sync_gateway dev build number (eg, 345)")

    parser.add_option("", "--sync-gateway-config-file",
                      action="store", type="string", dest="sync_gateway_config_file", default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file")

    parser.add_option("", "--sync-gateway-branch",
                      action="store", type="string", dest="source_branch", default=None,
                      help="sync_gateway branch to checkout and build")

    parser.add_option("", "--install-deps", action="store_true", dest="install_deps", default=False,
                      help="This flag will install the required dependencies to build sync_gateway from source")

    parser.add_option("", "--skip-bucketflush",
                      action="store", dest="skip_bucketflush", default=False,
                      help="skip the bucketflush step")

    parser.add_option("", "--build-flags",
                      action="store", type="string", dest="build_flags", default="",
                      help="build flags to pass when building sync gateway (ex. -race)")

    
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    server_config = CouchbaseServerConfig(
        version=opts.server_version
    )

    sync_gateway_version = None
    sync_gateway_build = None

    if opts.sync_gateway_version is not None:
        version_build = opts.sync_gateway_version.split("-")
        if len(version_build) != 2:
            print("Make sure the sync_gateway version follows pattern: 1.2.3-456")
            sys.exit(1)
        sync_gateway_version = version_build[0]
        sync_gateway_build = version_build[1]

    sync_gateway_config = SyncGatewayConfig(
        version=sync_gateway_version,
        build_number=sync_gateway_build,
        dev_build_url=opts.sync_gateway_dev_build_url,
        dev_build_number=opts.sync_gateway_dev_build_number,
        branch=opts.source_branch,
        build_flags=opts.build_flags,
        config_path=opts.sync_gateway_config_file,
        skip_bucketflush=opts.skip_bucketflush
    )

    provision_cluster(
        couchbase_server_config=server_config,
        sync_gateway_config=sync_gateway_config,
        install_deps=opts.install_deps
    )
