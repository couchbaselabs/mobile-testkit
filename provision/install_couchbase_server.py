import os
import sys
from optparse import OptionParser

import ansible_runner


class CouchbaseServerConfig:

    def __init__(self, version):

        self._valid_versions = [
            "3.1.0",
            "3.1.1",
            "3.1.2",
            "4.0.0",
            "4.1.0"
        ]

        self._version = version

    def _base_url_package_for_server(self, version):
        if version == "3.1.0":
            base_url = "http://latestbuilds.hq.couchbase.com"
            package_name = "couchbase-server-enterprise_centos6_x86_64_3.1.0-1805-rel.rpm"
            return base_url, package_name
        elif version == "3.1.1":
            base_url = "http://latestbuilds.hq.couchbase.com"
            package_name = "couchbase-server-enterprise_centos6_x86_64_3.1.1-1807-rel.rpm"
            return base_url, package_name
        elif version == "3.1.2":
            base_url = "http://latestbuilds.hq.couchbase.com"
            package_name = "couchbase-server-enterprise_centos6_x86_64_3.1.2-1815-rel.rpm"
            return base_url, package_name
        elif version == "4.0.0":
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-server/sherlock/4051"
            package_name = "couchbase-server-enterprise-4.0.0-4051-centos7.x86_64.rpm"
            return base_url, package_name
        elif version == "4.1.0":
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-server/sherlock/5005"
            package_name = "couchbase-server-enterprise-4.1.0-5005-centos7.x86_64.rpm"
            return base_url, package_name
        else:
            print "Server package url not found. Make sure to specify a version / build."
            sys.exit(1)

    @property
    def version(self):
        return self._version

    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self._version)
        return output

    def server_base_url_and_package(self):
        return self._base_url_package_for_server(self._version)

    def is_valid(self):
        if self._version not in self._valid_versions:
            print "Make sure your server version is one of the following: {}".format(self._valid_versions)
            return False
        return True


def install_couchbase_server(couchbase_server_config):

    print(couchbase_server_config)

    if not couchbase_server_config.is_valid():
        print "Invalid server provisioning configuration. Exiting ..."
        sys.exit(1)

    server_base_url, server_package_name = couchbase_server_config.server_base_url_and_package()

    ansible_runner.run_ansible_playbook(
        "install-couchbase-server-package.yml",
        "couchbase_server_package_base_url={0} couchbase_server_package_name={1}".format(
            server_base_url,
            server_package_name
        )
    )

if __name__ == "__main__":
    usage = "usage: python install_couchbase_server.py --version=<couchbase_server_version> --build-number=<server_build_number>"

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="server version to download")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    server_config = CouchbaseServerConfig(
        version=opts.version
    )

    install_couchbase_server(server_config)
