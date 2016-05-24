import os
import sys
import logging
from optparse import OptionParser

import install_sync_gateway
import install_couchbase_server

from install_couchbase_server import CouchbaseServerConfig
from install_sync_gateway import SyncGatewayConfig

from ansible_runner import AnsibleRunner
from robot.api.logger import console

def provision_cluster(couchbase_server_config, sync_gateway_config, install_deps):

    test_output("\n>>> Host info:\n")

    with open(os.environ["CLUSTER_CONFIG"], "r") as ansible_hosts:
        test_output(ansible_hosts.read())

    test_output(couchbase_server_config)
    test_output(sync_gateway_config)

    if not sync_gateway_config.is_valid():
        test_output("Invalid sync_gateway provisioning configuration. Exiting ...")
        sys.exit(1)

    test_output(">>> Provisioning cluster...")

    # Get server base url and package name
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package()

    test_output(">>> Server package: {0}/{1}".format(server_baseurl, server_package_name))
    test_output(">>> Using sync_gateway config: {}".format(sync_gateway_config.config_path))

    ansible_runner = AnsibleRunner()

    # Reset previous installs
    status = ansible_runner.run_ansible_playbook("remove-previous-installs.yml", stop_on_fail=False)
    assert(status == 0)

    if install_deps:
        # OS-level modifications
        status = ansible_runner.run_ansible_playbook("os-level-modifications.yml", stop_on_fail=False)
        assert(status == 0)

        # Install dependencies
        status = ansible_runner.run_ansible_playbook("install-common-tools.yml", stop_on_fail=False)
        assert(status == 0)

    # Clear firewall rules
    status = ansible_runner.run_ansible_playbook("flush-firewall.yml", stop_on_fail=False)
    assert(status == 0)

    # Install server package
    install_couchbase_server.install_couchbase_server(couchbase_server_config)

    # Install sync_gateway
    install_sync_gateway.install_sync_gateway(sync_gateway_config)

def test_output(output):
    console(output)
    logging.info(output)

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

    default_sync_gateway_config = os.path.abspath("resources/sync_gateway_configs/sync_gateway_default.json")

    parser.add_option("", "--server-version",
                      action="store", type="string", dest="server_version", default=None,
                      help="server version to download")

    parser.add_option("", "--sync-gateway-version",
                      action="store", type="string", dest="sync_gateway_version", default=None,
                      help="sync_gateway release version to download (ex. 1.2.0-5)")

    parser.add_option("", "--sync-gateway-config-file",
                      action="store", type="string", dest="sync_gateway_config_file", default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file, uses 'resources/sync_gateway_configs/sync_gateway_default.json' by default")

    parser.add_option("", "--sync-gateway-commit",
                      action="store", type="string", dest="source_commit", default=None,
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

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

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
        version_number=sync_gateway_version,
        build_number=sync_gateway_build,
        commit=opts.source_commit,
        build_flags=opts.build_flags,
        config_path=opts.sync_gateway_config_file,
        skip_bucketflush=opts.skip_bucketflush
    )

    provision_cluster(
        couchbase_server_config=server_config,
        sync_gateway_config=sync_gateway_config,
        install_deps=opts.install_deps
    )
