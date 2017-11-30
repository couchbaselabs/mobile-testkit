import os
import sys
from optparse import OptionParser

from libraries.provision.ansible_runner import AnsibleRunner

from keywords.exceptions import ProvisioningError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import CouchbaseServer
from keywords.utils import log_info


class CouchbaseServerConfig:

    def __init__(self, version):
        """
        The Couchbase Server version will either be of the form:

        4.5.0 (eg, no build number specified)

        OR

        4.5.0-2601 (a particular build number is specified)

        """

        version_build = version.split("-")
        self.version = version_build[0]
        if len(version_build) == 2:
            # Build number is included
            self.build = version_build[1]
        else:
            self.build = None

    def get_baseurl_package(self, cb_server, cbs_platform="centos7"):

        if self.build is None:
            # since the user didn't specify a build number,
            # this means user wants an official released version, so
            # return cbmobile-packages bucket url
            return cb_server.resolve_cb_mobile_url(self.version, cbs_platform=cbs_platform)
        else:
            # the user specified an explicit build number, so grab the
            # build off the "cbnas" server (Couchbase VPN only)
            return cb_server.resolve_cb_nas_url(self.version, self.build, cbs_platform=cbs_platform)

    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.version)
        return output


def install_couchbase_server(cluster_config, couchbase_server_config, cbs_platform="centos7"):

    log_info(cluster_config)
    log_info(couchbase_server_config)

    ansible_runner = AnsibleRunner(cluster_config)
    cluster_keywords = ClusterKeywords()
    cluster_topology = cluster_keywords.get_cluster_topology(cluster_config)
    server_url = cluster_topology["couchbase_servers"][0]
    cb_server = CouchbaseServer(server_url)

    log_info(">>> Installing Couchbase Server")
    # Install Server
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package(cb_server, cbs_platform)
    status = ansible_runner.run_ansible_playbook(
        "install-couchbase-server-package.yml",
        extra_vars={
            "couchbase_server_package_base_url": server_baseurl,
            "couchbase_server_package_name": server_package_name
        }
    )
    if status != 0:
        raise ProvisioningError("Failed to install Couchbase Server")

    # Wait for server to be in 'healthy state'
    print(">>> Waiting for server to be in 'healthy' state")
    cb_server.wait_for_ready_state()


if __name__ == "__main__":
    usage = "usage: python install_couchbase_server.py --version=<couchbase_server_version> --build-number=<server_build_number>"

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="server version to download")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    server_config = CouchbaseServerConfig(
        version=opts.version
    )

    install_couchbase_server(
        cluster_config=cluster_conf,
        couchbase_server_config=server_config
    )
