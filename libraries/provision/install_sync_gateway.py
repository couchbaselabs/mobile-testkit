import os
import re
import sys
from optparse import OptionParser

from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import CouchbaseServer
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info, log_warn
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.config import Config
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled


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
            "1.3.1",
            "1.3.1.2",
            "1.4.0",
            "1.4",
            "1.4.0.1",
            "1.4.0.2",
            "1.4.1",
            "1.4.1.1",
            "1.4.2",
            "1.5.0"
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

    def sync_gateway_base_url_and_package(self, sg_ce=False):
        if self._version_number == "1.1.0" or self._build_number == "1.1.1":
            log_info("Version unsupported in provisioning.")
            raise ProvisioningError("Unsupport version of sync_gateway")
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/1.1.1/1.1.1-10/couchbase-sync-gateway-enterprise_1.1.1-10_x86_64.rpm
            # base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/release/{0}/{1}-{2}".format(version, version, build)
            # sg_package_name  = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        else:
            # http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.0/1.2.0-6/couchbase-sync-gateway-enterprise_1.2.0-6_x86_64.rpm
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/{0}/{1}-{2}".format(self._version_number, self._version_number, self._build_number)

            sg_type = "enterprise"

            if sg_ce:
                sg_type = "community"

            sg_package_name = "couchbase-sync-gateway-{0}_{1}-{2}_x86_64.rpm".format(sg_type, self._version_number, self._build_number)
            accel_package_name = "couchbase-sg-accel-enterprise_{0}-{1}_x86_64.rpm".format(self._version_number, self._build_number)
        return base_url, sg_package_name, accel_package_name

    def is_valid(self):
        if self._version_number is not None and self._build_number is not None:
            if self.commit is not None:
                raise ProvisioningError("Commit should be empty when provisioning with a binary")
            if self._version_number not in self._valid_versions:
                raise ProvisioningError("Could not find version in valid versions")
        elif self.commit is not None:
            if self._version_number is not None:
                raise ProvisioningError("Do not specify a version number when provisioning via a commit.")
            if self._build_number is not None:
                raise ProvisioningError("Do not specify a build number when provisioning via a commit.")
        else:
            log_info("You must provide a (version and build number) or (dev url and dev build number) or commit to build for sync_gateway")
            return False

        if not os.path.isfile(self.config_path):
            log_info("Could not find sync_gateway config file: {}".format(self.config_path))
            log_info("Try to use an absolute path.")
            return False

        return True


def install_sync_gateway(cluster_config, sync_gateway_config, sg_ce=False):
    log_info(sync_gateway_config)

    if not sync_gateway_config.is_valid():
        raise ProvisioningError("Invalid sync_gateway provisioning configuration. Exiting ...")

    if sync_gateway_config.build_flags != "":
        log_warn("\n\n!!! WARNING: You are building with flags: {} !!!\n\n".format(sync_gateway_config.build_flags))

    ansible_runner = AnsibleRunner(cluster_config)
    config_path = os.path.abspath(sync_gateway_config.config_path)

    # Create buckets unless the user explicitly asked to skip this step
    if not sync_gateway_config.skip_bucketcreation:
        create_server_buckets(cluster_config, sync_gateway_config)

    server_port = 8091
    server_scheme = "http"

    if is_cbs_ssl_enabled(cluster_config):
        server_port = 18091
        server_scheme = "https"

    # Shared vars
    playbook_vars = {
        "sync_gateway_config_filepath": config_path,
        "server_port": server_port,
        "server_scheme": server_scheme,
        "autoimport": "",
        "xattrs": ""
    }

    if is_xattrs_enabled(cluster_config):
        playbook_vars["autoimport"] = '"import_docs": "continuous",'
        playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

    # Install Sync Gateway via Source or Package
    if sync_gateway_config.commit is not None:
        # Install from source
        playbook_vars["commit"] = sync_gateway_config.commit
        playbook_vars["build_flags"] = sync_gateway_config.build_flags

        status = ansible_runner.run_ansible_playbook(
            "install-sync-gateway-source.yml",
            extra_vars=playbook_vars
        )
        if status != 0:
            raise ProvisioningError("Failed to install sync_gateway source")

    else:
        # Install from Package
        sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sync_gateway_config.sync_gateway_base_url_and_package(sg_ce)

        playbook_vars["couchbase_sync_gateway_package_base_url"] = sync_gateway_base_url
        playbook_vars["couchbase_sync_gateway_package"] = sync_gateway_package_name
        playbook_vars["couchbase_sg_accel_package"] = sg_accel_package_name

        status = ansible_runner.run_ansible_playbook(
            "install-sync-gateway-package.yml",
            extra_vars=playbook_vars
        )
        if status != 0:
            raise ProvisioningError("Failed to install sync_gateway package")

    # Configure aws cloudwatch logs forwarder
    status = ansible_runner.run_ansible_playbook(
        "configure-sync-gateway-awslogs-forwarder.yml",
        extra_vars={}
    )
    if status != 0:
        raise ProvisioningError("Failed to configure sync_gateway awslogs forwarder")


def create_server_buckets(cluster_config, sync_gateway_config):

    # get the couchbase server url
    cluster_helper = ClusterKeywords()
    cluster_topology = cluster_helper.get_cluster_topology(cluster_config)

    # Handle the case of resources/cluster_configs/1sg, where we are targeting a
    #   sync_gateway without a backing server
    if len(cluster_topology["couchbase_servers"]) == 0:
        log_info("The cluster_config: {} does not have a couchbase server. Skipping bucket creation!!".format(cluster_config))
        return

    couchbase_server_url = cluster_topology["couchbase_servers"][0]

    # delete existing buckets
    cb_server = CouchbaseServer(couchbase_server_url)
    cb_server.delete_buckets()

    # find bucket names from sg config
    bucket_names = get_buckets_from_sync_gateway_config(sync_gateway_config.config_path)

    # create couchbase server buckets
    cb_server.create_buckets(bucket_names)


def get_buckets_from_sync_gateway_config(sync_gateway_config_path):
    # Remove the sync function before trying to extract the bucket names

    with open(sync_gateway_config_path) as fp:
        conf_data = fp.read()

    fp.close()
    temp_config_path = ""
    temp_config = ""

    # Check if a sync function id defined between ` `
    if re.search('`', conf_data):
        log_info("Ignoring the sync function to extract bucket names")
        conf = re.split('`', conf_data)
        split_len = len(conf)

        # Replace the sync function with a string "function"
        for i in range(0, split_len, 2):
            if i == split_len - 1:
                temp_config += conf[i]
            else:
                temp_config += conf[i] + " \"function\" "

        temp_config_path = "/".join(sync_gateway_config_path.split('/')[:-2]) + '/temp_conf.json'

        with open(temp_config_path, 'w') as fp:
            fp.write(temp_config)

        config_path_full = os.path.abspath(temp_config_path)
    else:
        config_path_full = os.path.abspath(sync_gateway_config_path)

    config = Config(config_path_full)
    bucket_name_set = config.get_bucket_name_set()
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)
    return bucket_name_set


if __name__ == "__main__":
    usage = """usage: python install_sync_gateway.py
    --commit=<sync_gateway_commit_to_build>
    """

    default_sync_gateway_config = os.path.abspath("resources/sync_gateway_configs/sync_gateway_default_di.json")

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="sync_gateway version to download (ex. 1.2.0-5)")

    parser.add_option("", "--config-file-path",
                      action="store", type="string", dest="sync_gateway_config_file",
                      default=default_sync_gateway_config,
                      help="path to your sync_gateway_config file uses 'resources/sync_gateway_configs/sync_gateway_default_di.json' by default")

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
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    version = None
    build = None

    if opts.version is not None:
        version_build = opts.version.split("-")
        if len(version_build) != 2:
            log_info("Make sure the sync_gateway version follows pattern: 1.2.3-456")
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

    install_sync_gateway(
        cluster_config=cluster_conf,
        sync_gateway_config=sync_gateway_install_config
    )
