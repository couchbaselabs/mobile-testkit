import os
import sys
from optparse import OptionParser
import json

from ansible_runner import AnsibleRunner

from keywords.exceptions import ProvisioningError
from keywords.ClusterKeywords import ClusterKeywords
from keywords.CouchbaseServer import CouchbaseServer
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

    def get_baseurl_package(self):

        if self.build is None:
            # since the user didn't specify a build number,
            # this means user wants an official released version, so
            # return cbmobile-packages bucket url
            return resolve_cb_mobile_url(self.version)
        else:
            # the user specified an explicit build number, so grab the
            # build off the "cbnas" server (Couchbase VPN only)
            return resolve_cb_nas_url(self.version, self.build)


    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.version)
        return output


def resolve_cb_mobile_url(version):
    """
    Resolve a download URL for the corresponding package to given
    version on http://cbmobile-packages.s3.amazonaws.com (an S3 bucket
    for couchbase mobile that mirrors released couchbase server versions)

    Given:

    version - the version without any build number information, eg 4.5.0

    Return the base_url of the package download URL (everything except the filename)

    """
    released_versions = {
        "4.5.0": "2601",
        "4.1.1": "5914",
        "4.1.0": "5005",
        "4.0.0": "4051",
        "3.1.5": "1859"
    }
    build_number = released_versions[version]
    base_url = "http://cbmobile-packages.s3.amazonaws.com"
    package_name = get_package_name(version, build_number)
    return base_url, package_name


def resolve_cb_nas_url(version, build_number):
    """
    Resolve a download URL for couchbase server on the internal VPN download site

    Given:

    version - the version without any build number information, eg 4.5.0
    build_number - the build number associated with this major version release, eg, 2601 (or None)

    Return the base_url of the package download URL (everything except the filename)

    """

    cbnas_base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server"

    if version.startswith("3.1"):
        base_url = "http://latestbuilds.hq.couchbase.com/"
    elif version.startswith("4.0") or version.startswith("4.1"):
        base_url = "{}/sherlock/{}".format(cbnas_base_url, build_number)
    elif version.startswith("4.5") or version.startswith("4.6"):
        base_url = "{}/watson/{}".format(cbnas_base_url, build_number)
    elif version.startswith("4.7"):
        base_url = "{}/spock/{}".format(cbnas_base_url, build_number)
    else:
        raise Exception("Unexpected couchbase server version: {}".format(version))

    package_name = get_package_name(version, build_number)
    return base_url, package_name


def get_package_name(version, build_number):
    """
    Given:

    version - the version without any build number information, eg 4.5.0
    build_number - the build number associated with this major version release, eg, 2601 (or None)

    Return the filename portion of the package download URL

    """

    if version.startswith("3.1"):
        return "couchbase-server-enterprise_centos6_x86_64_{}-{}-rel.rpm".format(version, build_number)
    else:
        return "couchbase-server-enterprise-{}-{}-centos7.x86_64.rpm".format(version, build_number)


def install_couchbase_server(cluster_config, couchbase_server_config):

    log_info(cluster_config)
    log_info(couchbase_server_config)

    ansible_runner = AnsibleRunner(cluster_config)

    log_info(">>> Installing Couchbase Server")
    # Install Server
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package()
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
    cluster_keywords = ClusterKeywords()
    cluster_topology = cluster_keywords.get_cluster_topology(os.environ["CLUSTER_CONFIG"])
    server = cluster_topology["couchbase_servers"][0]
    server_keywords = CouchbaseServer()
    server_keywords.wait_for_ready_state(server)


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
