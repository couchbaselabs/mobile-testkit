import sys
import os
from optparse import OptionParser

import ansible_runner


class SyncGatewayConfig:

    def __init__(self,
                 branch,
                 version,
                 build_number,
                 config_path):
        self.__version = version
        self.__build_number = build_number
        self.__branch = branch
        self.__config_path = config_path

    @property
    def version(self):
        return self.__version

    @property
    def build_number(self):
        return self.__build_number

    @property
    def branch(self):
        return self.__branch

    @property
    def config_path(self):
        return self.__config_path

    def __str__(self):
        output = "\n  sync_gateway configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.__version)
        output += "  build number: {}\n".format(self.__build_number)
        output += "  branch:       {}\n".format(self.__branch)
        output += "  config path:  {}\n".format(self.__config_path)
        return output

    def __base_url_package_for_sync_gateway(self, version, build):
        base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/{0}/{1}-{2}".format(version, version, build)
        package_name = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        return base_url, package_name

    def sync_gateway_base_url_and_package(self):
        return self.__base_url_package_for_sync_gateway(self.__version, self.__build_number)

    def is_valid(self):
        if self.__version is None and self.__branch is None:
            print "You must provide a version / build or branch to build for sync_gateway"
            return False
        if self.__branch is not None and (self.__version is not None or self.__build_number is not None):
            print "Specify --branch or --version, not both"
            return False
        if self.__version is not None and self.__build_number is None:
            print "Must specify a build number for sync_gateway version"
            return False
        if self.__version is None and self.__build_number is not None:
            print "Please specify both a version and build number for sync_gateway build"
            return False
        if not os.path.isfile(self.__config_path):
            print "Could not find sync_gateway config file: {}".format(self.__config_path)
            print "Try to use an absolute path."
            return False
        return True


def install_sync_gateway(sync_gateway_config):

    print(sync_gateway_config)

    if not sync_gateway_config.is_valid():
        print "Invalid server provisioning configuration. Exiting ..."
        sys.exit(1)

    if sync_gateway_config.branch != "":
        print "Build from source with branch: {}".format(sync_gateway_config.branch)
        ansible_runner.run_ansible_playbook("build-sync-gateway-source.yml", "branch={}".format(sync_gateway_config.branch))
    else:
        print "Build stable"
        sync_gateway_base_url, sync_gateway_package_name = sync_gateway_config.sync_gateway_base_url_and_package()
        ansible_runner.run_ansible_playbook(
            "install-sync-gateway-package.yml",
            "couchbase_sync_gateway_package_base_url={0} couchbase_sync_gateway_package={1}".format(
                sync_gateway_base_url,
                sync_gateway_package_name
            )
        )

    ansible_runner.run_ansible_playbook("install-sync-gateway-service.yml", "sync_gateway_config_filepath={}".format(sync_gateway_config.config_path))

if __name__ == "__main__":
    usage = """usage: python install_sync_gateway.py
    --branch=<sync_gateway_branch_to_build>
    --config-file-path=<path_to_local_sync_gateway_config>
    """

    default_sync_gateway_config = os.path.abspath("../ansible/playbooks/files/sync_gateway_config.json")

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="sync_gateway version to download")

    parser.add_option("", "--build-number",
                      action="store", type="string", dest="build_number", default=None,
                      help="sync_gateway build to download")

    parser.add_option("", "--config-file-path",
                      action="store", type="string", dest="sync_gateway_config_file", default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file")

    parser.add_option("", "--branch",
                      action="store", type="string", dest="source_branch", default=None,
                      help="sync_gateway branch to checkout and build")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    sync_gateway_install_config = SyncGatewayConfig(
        version=opts.version,
        build_number=opts.build_number,
        branch=opts.source_branch,
        config_path=opts.sync_gateway_config_file
    )

    install_sync_gateway(sync_gateway_install_config)