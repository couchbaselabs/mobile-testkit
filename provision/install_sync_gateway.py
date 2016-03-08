import sys
import os
from optparse import OptionParser

import ansible_runner


class SyncGatewayConfig:
    def __init__(self,
                 branch,
                 dev_build_url,
                 dev_build_number,
                 version,
                 build_number,
                 config_path,
                 build_flags,
                 skip_bucketflush):

        self._dev_build_url = dev_build_url
        self._dev_build_number = dev_build_number
        self._version = version
        self._build_number = build_number
        self._branch = branch
        self._config_path = config_path
        self._build_flags = build_flags
        self._skip_bucketflush = skip_bucketflush
        
        self._valid_versions = [
            "1.1.0",
            "1.1.1",
            "1.2.0",
            "1.2.1",
            "1.3.0"
        ]

    @property
    def dev_build_url(self):
        return self._dev_build_url

    @property
    def dev_build_number(self):
        return self._dev_build_number

    @property
    def build_number(self):
        return self._build_number

    @property
    def version(self):
        return self._version

    @property
    def build_number(self):
        return self._build_number

    @property
    def branch(self):
        return self._branch

    @property
    def config_path(self):
        return self._config_path
    
    @property
    def build_flags(self):
        return self._build_flags

    @property
    def skip_bucketflush(self):
        return self._skip_bucketflush

    
    def __str__(self):
        output = "\n  sync_gateway configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:          {}\n".format(self._version)
        output += "  build number:     {}\n".format(self._build_number)
        output += "  dev build url:    {}\n".format(self._dev_build_url)
        output += "  dev build number: {}\n".format(self._dev_build_number)
        output += "  branch:           {}\n".format(self._branch)
        output += "  config path:      {}\n".format(self._config_path)
        output += "  build flags:      {}\n".format(self._build_flags)
        output += "  skip bucketflush: {}\n".format(self._skip_bucketflush)
        return output

    def _base_url_package_for_sync_gateway_dev_build(self, dev_build_url, dev_build_number):
        # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/0.0.1/feature/distributed_index/0.0.1-449/couchbase-sync-gateway-community_0.0.1-449_x86_64.rpm
        base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/0.0.1/{0}/0.0.1-{1}".format(dev_build_url, dev_build_number)
        sg_package_name = "couchbase-sync-gateway-community_0.0.1-{0}_x86_64.rpm".format(dev_build_number)
        accel_package_name = "couchbase-sg-accel-community_0.0.1-{0}_x86_64.rpm".format(dev_build_number)
        return base_url, sg_package_name, accel_package_name

    def _base_url_package_for_sync_gateway(self, version, build):
        if version == "1.1.0" or version == "1.1.1":
            print("Version unsupported in provisioning.")
            sys.exit(1)
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/1.1.1/1.1.1-10/couchbase-sync-gateway-enterprise_1.1.1-10_x86_64.rpm
            #base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/{0}/{1}-{2}".format(version, version, build)
            #sg_package_name  = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        else:
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.0/1.2.0-6/couchbase-sync-gateway-enterprise_1.2.0-6_x86_64.rpm
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/{0}/{1}-{2}".format(version, version, build)
            sg_package_name = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
            accel_package_name = "couchbase-sg-accel-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        return base_url, sg_package_name, accel_package_name

    def sync_gateway_base_url_and_package(self, dev_build=False):
        if not dev_build:
            return self._base_url_package_for_sync_gateway(self._version, self._build_number)
        else:
            return self._base_url_package_for_sync_gateway_dev_build(self._dev_build_url, self._dev_build_number)

    def is_valid(self):
        if self._version is not None and self._build_number is not None:
            assert self._dev_build_url is None
            assert self._dev_build_number is None
            assert self._branch is None
            assert self._version in self._valid_versions
        elif self._dev_build_url is not None and self._dev_build_number is not None:
            assert self._version is None
            assert self._build_number is None
            assert self._branch is None
        elif self._branch is not None:
            assert self._dev_build_url is None
            assert self._dev_build_number is None
            assert self._version is None
            assert self._build_number is None
        else:
            print "You must provide a (version and build number) or (dev url and dev build number) or branch to build for sync_gateway"
            return False

        if not os.path.isfile(self._config_path):
            print "Could not find sync_gateway config file: {}".format(self._config_path)
            print "Try to use an absolute path."
            return False

        return True


def install_sync_gateway(sync_gateway_config):
    print(sync_gateway_config)

    if not sync_gateway_config.is_valid():
        print "Invalid sync_gateway provisioning configuration. Exiting ..."
        sys.exit(1)

    if sync_gateway_config.build_flags != "":
        print("\n\n!!! WARNING: You are building with flags: {} !!!\n\n".format(sync_gateway_config.build_flags))

    if sync_gateway_config.branch is not None:
                
        # Install source
        ansible_runner.run_ansible_playbook(
            "install-sync-gateway-source.yml",
            "sync_gateway_config_filepath={0} branch={1} build_flags={2} skip_bucketflush={3}".format(
                sync_gateway_config.config_path,
                sync_gateway_config.branch,
                sync_gateway_config.build_flags,
                sync_gateway_config.skip_bucketflush
            )
        )

    else:
        # Install build
        if sync_gateway_config.dev_build_url is not None:
            sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sync_gateway_config.sync_gateway_base_url_and_package(dev_build=True)
        else:
            sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sync_gateway_config.sync_gateway_base_url_and_package()

        ansible_runner.run_ansible_playbook(
            "install-sync-gateway-package.yml",
            "couchbase_sync_gateway_package_base_url={0} couchbase_sync_gateway_package={1} couchbase_sg_accel_package={2} sync_gateway_config_filepath={3} skip_bucketflush={4}".format(
                sync_gateway_base_url,
                sync_gateway_package_name,
                sg_accel_package_name,
                sync_gateway_config.config_path,
                sync_gateway_config.skip_bucketflush
            )
        )

if __name__ == "__main__":
    usage = """usage: python install_sync_gateway.py
    --branch=<sync_gateway_branch_to_build>
    """

    default_sync_gateway_config = os.path.abspath("conf/sync_gateway_default.json")

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="sync_gateway version to download (ex. 1.2.0-5)")

    parser.add_option("", "--config-file-path",
                      action="store", type="string", dest="sync_gateway_config_file",
                      default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file uses '/conf/default_sync_gateway_config' by default")

    parser.add_option("", "--branch",
                      action="store", type="string", dest="source_branch", default=None,
                      help="sync_gateway branch to checkout and build")

    parser.add_option("", "--dev-build-url",
                      action="store", type="string", dest="dev_build_url", default=None,
                      help="sync_gateway dev build url (ex. 'feature/distributed_index')")

    parser.add_option("", "--dev-build-number",
                      action="store", type="string", dest="dev_build_number", default=None,
                      help="sync_gateway dev build number (ex. 340)")

    parser.add_option("", "--build-flags",
                      action="store", type="string", dest="build_flags", default="",
                      help="build flags to pass when building sync gateway (ex. -race)")

    parser.add_option("", "--skip-bucketflush",
                      action="store", dest="skip_bucketflush", default=False,
                      help="skip the bucketflush step")

    
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    
    version = None
    build = None

    if opts.version is not None:
        version_build = opts.version.split("-")
        if len(version_build) != 2:
            print("Make sure the sync_gateway version follows pattern: 1.2.3-456")
            sys.exit(1)
        version = version_build[0]
        build = version_build[1]

    sync_gateway_install_config = SyncGatewayConfig(
        version=version,
        build_number=build,
        branch=opts.source_branch,
        config_path=opts.sync_gateway_config_file,
        dev_build_url=opts.dev_build_url,
        dev_build_number=opts.dev_build_number,
        build_flags=opts.build_flags,
        skip_bucketflush=opts.skip_bucketflush
    )

    install_sync_gateway(sync_gateway_install_config)

