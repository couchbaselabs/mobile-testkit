import os
import re
import sys
from optparse import OptionParser

from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import CouchbaseServer
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info, log_warn, add_cbs_to_sg_config_server_field
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.config import Config
from libraries.testkit.cluster import Cluster
from keywords.constants import SYNC_GATEWAY_CERT
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, get_revs_limit, sg_ssl_enabled
from utilities.cluster_config_utils import is_hide_prod_version_enabled, get_cbs_primary_nodes_str
from utilities.cluster_config_utils import get_sg_version, get_sg_replicas, get_sg_use_views, get_redact_level, is_x509_auth, generate_x509_certs, is_delta_sync_enabled


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

    def resolve_sg_sa_mobile_url(self, installer="sync-gateway",
                                 sg_type="enterprise",
                                 platform_extension="rpm", aws=False):
        if self._build_number:
            base_url = "http://latestbuilds.service.couchbase.com/builds/latestbuilds/sync_gateway/{}/{}".format(self._version_number,
                                                                                                                 self._build_number)
            package_name = "couchbase-{}-{}_{}-{}_x86_64.{}".format(installer,
                                                                    sg_type,
                                                                    self._version_number,
                                                                    self._build_number,
                                                                    platform_extension)
        else:
            base_url = "http://latestbuilds.service.couchbase.com/builds/releases/mobile/couchbase-sync-gateway/{}".format(self._version_number)
            package_name = "couchbase-{}-{}_{}_x86_64.{}".format(installer,
                                                                 sg_type,
                                                                 self._version_number,
                                                                 platform_extension)
        if aws:
            base_url = "https://cbmobile-packages.s3.amazonaws.com"
            package_name = "couchbase-{}-{}_{}-{}_x86_64.{}".format(installer,
                                                                    sg_type,
                                                                    self._version_number,
                                                                    self._build_number,
                                                                    platform_extension)
        return base_url, package_name

    def sync_gateway_base_url_and_package(self, sg_ce=False,
                                          sg_platform="centos",
                                          sg_installer_type="msi",
                                          sa_platform="centos",
                                          sa_installer_type="msi", aws=False):
        # Setting SG platform extension
        if "windows" in sg_platform:
            sg_platform_extension = "msi"
        elif "centos" in sg_platform:
            sg_platform_extension = "rpm"
        elif "ubuntu" in sg_platform:
            sg_platform_extension = "deb"
        elif "macos" in sg_platform:
            sg_platform_extension = "zip"

        # Setting SG Accel platform extension
        if "windows" in sa_platform:
            sa_platform_extension = "msi"
        elif "centos" in sa_platform:
            sa_platform_extension = "rpm"
        elif "ubuntu" in sa_platform:
            sa_platform_extension = "deb"
        elif "macos" in sa_platform:
            sg_platform_extension = "zip"

        if self._version_number == "1.1.0" or self._build_number == "1.1.1":
            log_info("Version unsupported in provisioning.")
            raise ProvisioningError("Unsupport version of sync_gateway")
            # http://latestbuilds.service.couchbase.com/couchbase-sync-gateway/release/1.1.1/1.1.1-10/couchbase-sync-gateway-enterprise_1.1.1-10_x86_64.rpm
            # base_url = "http://latestbuilds.service.couchbase.com/couchbase-sync-gateway/release/{0}/{1}-{2}".format(version, version, build)
            # sg_package_name  = "couchbase-sync-gateway-enterprise_{0}-{1}_x86_64.rpm".format(version, build)
        else:
            # http://latestbuilds.service.couchbase.com/builds/latestbuilds/sync_gateway/1.3.1.5/2/couchbase-sync-gateway-enterprise_1.2.0-6_x86_64.rpm
            sg_type = "enterprise"

            if sg_ce:
                sg_type = "community"

            if (sg_platform == "windows" or sa_platform == "windows") and \
                    (sg_installer_type != "msi" or sa_installer_type != "msi"):
                sg_platform_extension = "exe"
                sa_platform_extension = "exe"

            base_url, sg_package_name = self.resolve_sg_sa_mobile_url("sync-gateway", sg_type, sg_platform_extension, aws)
            base_url, accel_package_name = self.resolve_sg_sa_mobile_url("sg-accel", sg_type, sa_platform_extension, aws)

        return base_url, sg_package_name, accel_package_name

    def is_valid(self):
        if self._version_number is not None:
            if self.commit is not None:
                raise ProvisioningError("Commit should be empty when provisioning with a binary")
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

    def get_sg_version_build(self):
        return self._version_number, self._build_number


def install_sync_gateway(cluster_config, sync_gateway_config, sg_ce=False,
                         sg_platform="centos", sg_installer_type="msi",
                         sa_platform="centos", sa_installer_type="msi",
                         ipv6=False, aws=False):

    log_info(sync_gateway_config)

    if sync_gateway_config.build_flags != "":
        log_warn("\n\n!!! WARNING: You are building with flags: {} !!!\n\n".format(sync_gateway_config.build_flags))

    bucket_names = get_buckets_from_sync_gateway_config(
        sync_gateway_config.config_path)
    cbs_cert_path = os.path.join(os.getcwd(), "certs")
    ansible_runner = AnsibleRunner(cluster_config)
    config_path = os.path.abspath(sync_gateway_config.config_path)
    sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
    couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
    # Create buckets unless the user explicitly asked to skip this step
    if not sync_gateway_config.skip_bucketcreation:
        create_server_buckets(cluster_config, sync_gateway_config)

    server_port = 8091
    server_scheme = "http"

    if is_cbs_ssl_enabled(cluster_config):
        server_port = ""
        server_scheme = "couchbases"

    couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)
    # Shared vars
    playbook_vars = {
        "sync_gateway_config_filepath": config_path,
        "username": "",
        "password": "",
        "certpath": "",
        "keypath": "",
        "cacertpath": "",
        "x509_certs_dir": cbs_cert_path,
        "x509_auth": False,
        "sg_cert_path": sg_cert_path,
        "server_port": server_port,
        "server_scheme": server_scheme,
        "autoimport": "",
        "xattrs": "",
        "no_conflicts": "",
        "sslcert": "",
        "sslkey": "",
        "num_index_replicas": "",
        "sg_use_views": "",
        "revs_limit": "",
        "couchbase_server_primary_node": couchbase_server_primary_node,
        "delta_sync": "",
        "prometheus": "",
        "hide_product_version": ""
    }

    if get_sg_version(cluster_config) >= "2.1.0":
        logging_config = '"logging": {"debug": {"enabled": true}'
        try:
            redact_level = get_redact_level(cluster_config)
            playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
        except KeyError as ex:
            log_info("Keyerror in getting logging{}".format(ex))

            playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

        if get_sg_use_views(cluster_config):
            playbook_vars["sg_use_views"] = '"use_views": true,'
        else:
            num_replicas = get_sg_replicas(cluster_config)
            playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

        if sg_platform == "macos":
            sg_home_directory = "/Users/sync_gateway"
        elif sg_platform == "windows":
                sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
        else:
            sg_home_directory = "/home/sync_gateway"

        if is_x509_auth(cluster_config):
            playbook_vars[
                "certpath"] = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
            playbook_vars[
                "keypath"] = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
            playbook_vars[
                "cacertpath"] = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
            if sg_platform == "windows":
                playbook_vars["certpath"] = playbook_vars["certpath"].replace("/", "\\\\")
                playbook_vars["keypath"] = playbook_vars["keypath"].replace("/", "\\\\")
                playbook_vars["cacertpath"] = playbook_vars["cacertpath"].replace("/", "\\\\")
            playbook_vars["server_scheme"] = "couchbases"
            playbook_vars["server_port"] = ""
            playbook_vars["x509_auth"] = True
            generate_x509_certs(cluster_config, bucket_names, sg_platform)
        else:
            playbook_vars["username"] = '"username": "{}",'.format(
                bucket_names[0])
            playbook_vars["password"] = '"password": "password",'
    else:
        playbook_vars["logging"] = '"log": ["*"],'
        playbook_vars["username"] = '"username": "{}",'.format(
            bucket_names[0])
        playbook_vars["password"] = '"password": "password",'

    if is_cbs_ssl_enabled(cluster_config) and get_sg_version(cluster_config) >= "1.5.0":
        playbook_vars["server_scheme"] = "couchbases"
        playbook_vars["server_port"] = 11207
        block_http_vars = {}
        port_list = [8091, 8092, 8093, 8094, 8095, 8096, 11210, 11211]
        for port in port_list:
            block_http_vars["port"] = port
            status = ansible_runner.run_ansible_playbook(
                "block-http-ports.yml",
                extra_vars=block_http_vars
            )
            if status != 0:
                raise ProvisioningError("Failed to block port on SGW")

    if is_xattrs_enabled(cluster_config):
        playbook_vars["autoimport"] = '"import_docs": true,'
        playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

    if no_conflicts_enabled(cluster_config):
        playbook_vars["no_conflicts"] = '"allow_conflicts": false,'

    if sg_ssl_enabled(cluster_config):
        playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
        playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

    try:
        revs_limit = get_revs_limit(cluster_config)
        playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
    except KeyError:
        log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

    if is_delta_sync_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.5.0":
        playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

    if get_sg_version(cluster_config) >= "2.8.0":
        playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

    if is_hide_prod_version_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.8.1":
            playbook_vars["hide_product_version"] = '"hide_product_version": true,'

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
        sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sync_gateway_config.sync_gateway_base_url_and_package(
            sg_ce=sg_ce, sg_platform=sg_platform,
            sg_installer_type=sg_installer_type, sa_platform=sa_platform,
            sa_installer_type=sa_installer_type, aws=aws)

        playbook_vars["couchbase_sync_gateway_package_base_url"] = sync_gateway_base_url
        playbook_vars["couchbase_sync_gateway_package"] = sync_gateway_package_name
        playbook_vars["couchbase_sg_accel_package"] = sg_accel_package_name
        playbook_vars["couchbase_server_version"] = sync_gateway_config.get_sg_version_build()

        if sg_platform == "windows":
            status = ansible_runner.run_ansible_playbook(
                "install-sync-gateway-package-windows.yml",
                extra_vars=playbook_vars
            )
        elif sg_platform == "macos":
            status = ansible_runner.run_ansible_playbook(
                "install-sync-gateway-package-macos.yml",
                extra_vars=playbook_vars
            )
        else:
            status = ansible_runner.run_ansible_playbook(
                "install-sync-gateway-package.yml",
                extra_vars=playbook_vars
            )

        if status != 0:
            raise ProvisioningError("Failed to install sync_gateway package")

        if sa_platform == "windows":
            status = ansible_runner.run_ansible_playbook(
                "install-sg-accel-package-windows.yml",
                extra_vars=playbook_vars
            )
        else:
            status = ansible_runner.run_ansible_playbook(
                "install-sg-accel-package.yml",
                extra_vars=playbook_vars
            )
        if status != 0:
            raise ProvisioningError("Failed to install sg_accel package")

    # Configure aws cloudwatch logs forwarder
    status = ansible_runner.run_ansible_playbook(
        "configure-sync-gateway-awslogs-forwarder.yml",
        extra_vars={}
    )
    if status != 0:
        raise ProvisioningError("Failed to configure sync_gateway awslogs forwarder")


def create_server_buckets(cluster_config, sync_gateway_config):

    # get the couchbase server url
    cluster = Cluster(cluster_config)
    cluster_helper = ClusterKeywords(cluster_config)
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
    cb_server.create_buckets(bucket_names=bucket_names,
                             cluster_config=cluster_config,
                             ipv6=cluster.ipv6)


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

    parser.add_option("", "--sa-platform",
                      action="store", dest="sa_platform", default="centos",
                      help="Set the SGAccel OS platform")

    parser.add_option("", "--sg-platform",
                      action="store", dest="sg_platform", default="centos",
                      help="Set the SG OS platform")

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
        sync_gateway_config=sync_gateway_install_config,
        sa_platform=opts.sa_platform,
        sg_platform=opts.sg_platform
    )
