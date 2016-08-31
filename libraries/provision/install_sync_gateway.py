import sys
import os

from keywords.CouchbaseServer import CouchbaseServer
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.config import Config

from optparse import OptionParser

from ansible_runner import AnsibleRunner


class SyncGatewayConfig:
    def __init__(self,
                 commit,
                 version_number,
                 build_number,
                 config_path,
                 build_flags,
                 skip_bucketcreation):

        self._version_number = version_number
        self._build_number = build_number
        self._valid_versions = [
            "1.1.0",
            "1.1.1",
            "1.2.0",
            "1.2.1",
            "1.3.0",
            "1.3.1"
        ]

        self.commit = commit
        self.build_flags = build_flags
        self.config_path = config_path
        self.skip_bucketcreation = skip_bucketcreation

    def __str__(self):
        output = "\n  sync_gateway configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:          {}\n".format(self._version_number)
        output += "  build number:     {}\n".format(self._build_number)
        output += "  commit:           {}\n".format(self.commit)
        output += "  config path:      {}\n".format(self.config_path)
        output += "  build flags:      {}\n".format(self.build_flags)
        output += "  skip bucketcreation: {}\n".format(self.skip_bucketcreation)
        return output

    def sync_gateway_base_url_and_package(self):
        if self._version_number == "1.1.0" or self._build_number == "1.1.1":
            print("Version unsupported in provisioning.")
            raise ValueError("Unsupport version of sync_gateway")
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/1.1.1/1.1.1-10/couchbase-sync-gateway-enterprise_1.1.1-10_x86_64.rpm
            # base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/{0}/{1}-{2}".format(version, version, build)
            # sg_package_name  = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        else:
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.0/1.2.0-6/couchbase-sync-gateway-enterprise_1.2.0-6_x86_64.rpm
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/{0}/{1}-{2}".format(self._version_number, self._version_number, self._build_number)
            sg_package_name = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(self._version_number, self._build_number)
            accel_package_name = "couchbase-sg-accel-enterprise_{0}-{1}_x86_64.rpm".format(self._version_number, self._build_number)
        return base_url, sg_package_name, accel_package_name


    def is_valid(self):
        if self._version_number is not None and self._build_number is not None:
            assert self.commit is None
            assert self._version_number in self._valid_versions
        elif self.commit is not None:
            assert self._version_number is None
            assert self._build_number is None
        else:
            print "You must provide a (version and build number) or (dev url and dev build number) or commit to build for sync_gateway"
            return False

        if not os.path.isfile(self.config_path):
            print "Could not find sync_gateway config file: {}".format(self.config_path)
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

    ansible_runner = AnsibleRunner()
    config_path = os.path.abspath(sync_gateway_config.config_path)

    # Create buckets unless the user explicitly asked to skip this step
    if not sync_gateway_config.skip_bucketcreation:
        create_server_buckets(os.environ["CLUSTER_CONFIG"], sync_gateway_config)

    # Install Sync Gateway via Source or Package
    if sync_gateway_config.commit is not None:
        # Install from source
        status = ansible_runner.run_ansible_playbook(
            "install-sync-gateway-source.yml",
            extra_vars={
                "sync_gateway_config_filepath":config_path,
                "commit": sync_gateway_config.commit,
                "build_flags": sync_gateway_config.build_flags
            }
        )
        assert status == 0, "Failed to install sync_gateway source"

    else:
        # Install from Package
        sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sync_gateway_config.sync_gateway_base_url_and_package()
        status = ansible_runner.run_ansible_playbook(
            "install-sync-gateway-package.yml",
            extra_vars={
                "couchbase_sync_gateway_package_base_url": sync_gateway_base_url,
                "couchbase_sync_gateway_package": sync_gateway_package_name,
                "couchbase_sg_accel_package": sg_accel_package_name,
                "sync_gateway_config_filepath": config_path
            }
        )
        assert(status == 0), "Failed to install sync_gateway package"


def create_server_buckets(cluster_config, sync_gateway_config):

    # get the couchbase server url
    cluster_helper = ClusterKeywords()
    cluster_topology = cluster_helper.get_cluster_topology(cluster_config)
    couchbase_server_url = cluster_topology["couchbase_servers"][0]

    # delete existing buckets
    server_helper = CouchbaseServer()
    server_helper.delete_buckets(couchbase_server_url)

    # find bucket names from sg config
    bucket_names = get_buckets_from_sync_gateway_config(sync_gateway_config.config_path)

    # create couchbase server buckets
    server_helper.create_buckets(couchbase_server_url, bucket_names)

def get_buckets_from_sync_gateway_config(sync_gateway_config_path):

    config_path_full = os.path.abspath(sync_gateway_config_path)
    config = Config(config_path_full)
    bucket_name_set = config.get_bucket_name_set()
    return bucket_name_set


if __name__ == "__main__":
    usage = """usage: python install_sync_gateway.py
    --commit=<sync_gateway_commit_to_build>
    """

    default_sync_gateway_config = os.path.abspath("resources/sync_gateway_configs/sync_gateway_default.json")

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="sync_gateway version to download (ex. 1.2.0-5)")

    parser.add_option("", "--config-file-path",
                      action="store", type="string", dest="sync_gateway_config_file",
                      default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file uses 'resources/sync_gateway_configs/sync_gateway_default.json' by default")

    parser.add_option("", "--commit",
                      action="store", type="string", dest="commit", default=None,
                      help="sync_gateway commit to checkout and build")

    parser.add_option("", "--build-flags",
                      action="store", type="string", dest="build_flags", default="",
                      help="build flags to pass when building sync gateway (ex. -race)")

    parser.add_option("", "--skip-bucketcreation",
                      action="store", dest="skip_bucketcreation", default=False,
                      help="skip the bucketcreation step")
    
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")
    
    version = None
    build = None

    if opts.version is not None:
        version_build = opts.version.split("-")
        if len(version_build) != 2:
            print("Make sure the sync_gateway version follows pattern: 1.2.3-456")
            raise ValueError("Invalid format for sync_gateway version. Make sure to follow the patter '1.2.3-456'")
        version = version_build[0]
        build = version_build[1]

    sync_gateway_install_config = SyncGatewayConfig(
        version_number=version,
        build_number=build,
        commit=opts.commit,
        config_path=opts.sync_gateway_config_file,
        build_flags=opts.build_flags,
        skip_bucketcreation=opts.skip_bucketcreation
    )

    install_sync_gateway(sync_gateway_install_config)

