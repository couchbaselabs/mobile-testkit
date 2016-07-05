import os
import sys
from optparse import OptionParser
import json

from ansible_runner import AnsibleRunner

from keywords.ClusterKeywords import ClusterKeywords
from keywords.CouchbaseServer import CouchbaseServer

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

        released_versions = {
            "4.5.0": "2601",
            "4.1.1": "5914",
            "4.1.0": "5005",
            "4.0.0": "4051",
            "3.1.5": "1859",
            "4.5.0": "2601"
        }

        # Get the build number for released versions
        if self.version in released_versions and self.build is None:
            buildnum_for_release = released_versions[self.version]

        base_url = get_base_url(self.version, buildnum_for_release, self.build)
        package_name = get_package_name(self.version, buildnum_for_release)

        return base_url, package_name

    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.version)
        return output



def get_base_url(version, buildnum_for_release, user_specified_build):
    """
    Given:

    version - the version without any build number information, eg 4.5.0
    buildnum_for_release - the build number associated with this major version release, eg, 2601 (or None)
    user_specified_build - if the user requested a particular build, eg 2601 (or None)

    Return the base_url of the package download URL (everything except the filename)

    """

    # if the user did not specify a particular build, that means we are going to use
    # an official build, which is expected to be stored (mirrored) on a separate S3 bucket
    # (in order to not skew stats for packages.couchbase.com)
    if user_specified_build is None:
        return "http://cbmobile-packages.s3.amazonaws.com"

    cbnas_base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server"

    if version.startswith("3.1"):
        return "http://latestbuilds.hq.couchbase.com/"
    elif version.startswith("4.0") or version.startswith("4.1"):
        return "{}/sherlock/{}".format(cbnas_base_url, buildnum_for_release)
    elif version.startswith("4.5"):
        return "{}/watson/{}".format(cbnas_base_url, buildnum_for_release)
    elif version.startswith("4.7"):
        return "{}/spock/{}".format(cbnas_base_url, buildnum_for_release)
    else:
        raise Exception("Unexpected couchbase server version: {}".format(version))

def get_package_name(version, buildnum_for_release):
    """
    Given:

    version - the version without any build number information, eg 4.5.0
    buildnum_for_release - the build number associated with this major version release, eg, 2601 (or None)

    Return the filename portion of the package download URL

    """

    if version.startswith("3.1"):
        return "couchbase-server-enterprise_centos6_x86_64_{}-{}-rel.rpm".format(version, buildnum_for_release)
    else:
        return "couchbase-server-enterprise-{}-{}-centos7.x86_64.rpm".format(version, buildnum_for_release)


def install_couchbase_server(couchbase_server_config):

    print(couchbase_server_config)

    ansible_runner = AnsibleRunner()

    print(">>> Installing Couchbase Server")
    # Install Server
    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package()
    status = ansible_runner.run_ansible_playbook(
        "install-couchbase-server-package.yml",
        extra_vars={
            "couchbase_server_package_base_url": server_baseurl,
            "couchbase_server_package_name": server_package_name
        }
    )
    assert status == 0, "Failed to install Couchbase Server"

    print(">>> Creating server buckets")
    # Create default buckets
    status = ansible_runner.run_ansible_playbook(
        "create-server-buckets.yml",
        extra_vars={"bucket_names": ["data-bucket", "index-bucket"]}
    )
    assert status == 0, "Failed to create Couchbase Server buckets"

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
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    server_config = CouchbaseServerConfig(
        version=opts.version
    )

    install_couchbase_server(server_config)
