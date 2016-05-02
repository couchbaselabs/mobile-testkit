import os
import sys
from optparse import OptionParser

from ansible_runner import AnsibleRunner


class CouchbaseServerConfig:

    def __init__(self, version):

        version_build = version.split("-")
        self.version = version_build[0]
        if len(version_build) == 2:
            # Build number is included
            self.build = version_build[1]
        else:
            self.build = None

        self.released_versions = [
            "3.1.0",
            "3.1.1",
            "3.1.2",
            "3.1.3",
            "3.1.4",
            "3.1.5",
            "4.0.0",
            "4.1.0",
            "4.1.1"
        ]

    def get_baseurl_package(self):

        if self.build is None:
            if self.version not in self.released_versions:
                raise ValueError("Version not found in released versions: {}".format(self.version))

            # Download the server release from s3
            base_url = "https://s3.amazonaws.com/packages.couchbase.com/releases/{}".format(self.version)
            package_name = "couchbase-server-enterprise-{}-centos7.x86_64.rpm".format(self.version)

        else:

            # Get dev server package from latestbuilds
            if self.version.startswith("4.1"):
                # http://172.23.120.24/builds/latestbuilds/couchbase-server/sherlock/5914/couchbase-server-enterprise-4.1.1-5914-centos7.x86_64.rpm
                base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server/sherlock/{}".format(self.build)
                package_name = "couchbase-server-enterprise-{}-{}-centos7.x86_64.rpm".format(self.version, self.build)
            elif self.version.startswith("4.5"):
                # http://172.23.120.24/builds/latestbuilds/couchbase-server/watson/2151/couchbase-server-enterprise-4.5.0-2151-centos7.x86_64.rpm
                base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server/watson/{}".format(self.build)
                package_name = "couchbase-server-enterprise-{}-{}-centos7.x86_64.rpm".format(self.version, self.build)
            else:
                raise ValueError("Unable to resolve dev build for version: {}-{}".format(self.version, self.build))

        return base_url, package_name

    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.version)
        return output


def install_couchbase_server(couchbase_server_config):

    print(couchbase_server_config)

    ansible_runner = AnsibleRunner()

    server_baseurl, server_package_name = couchbase_server_config.get_baseurl_package()
    status = ansible_runner.run_ansible_playbook(
        "install-couchbase-server-package.yml",
        "couchbase_server_package_base_url={0} couchbase_server_package_name={1}".format(
            server_baseurl,
            server_package_name
        ),
        stop_on_fail=False
    )
    assert(status == 0)

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
