import os
import sys
from optparse import OptionParser

import ansible_runner


class CouchbaseServerConfig:

    def __init__(self,
                 version,
                 build_number):

        self.__valid_versions = [
            "3.1.0",
            "3.1.1",
            "4.0.0"
        ]

        self.__version = version
        self.__build_number = build_number

    def __base_url_package_for_server(self, version, build):
        if version == "3.1.0":
            base_url = "http://latestbuilds.hq.couchbase.com"
            package_name = "couchbase-server-enterprise_centos6_x86_64_3.1.0-1805-rel.rpm"
            return base_url, package_name
        elif version == "3.1.1":
            base_url = "http://latestbuilds.hq.couchbase.com"
            package_name = "couchbase-server-enterprise_centos6_x86_64_3.1.1-1807-rel.rpm"
            return base_url, package_name
        elif version == "4.0.0":
            base_url = "http://latestbuilds.hq.couchbase.com/couchbase-server/sherlock/{0}".format(build)
            package_name = "couchbase-server-enterprise-{0}-{1}-centos7.x86_64.rpm".format(version, build)
            return base_url, package_name
        else:
            print "Server package url not found. Make sure to specify a version / build."
            sys.exit(1)

    @property
    def version(self):
        return self.__version

    @property
    def build_number(self):
        return self.__build_number

    def __str__(self):
        output = "\n  Couchbase Server configuration\n"
        output += "  ------------------------------------------\n"
        output += "  version:      {}\n".format(self.__version)
        output += "  build number: {}\n".format(self.__build_number)
        return output

    def server_base_url_and_package(self):
        return self.__base_url_package_for_server(self.__version, self.__build_number)

    def is_valid(self):
        if self.__version not in self.__valid_versions:
            print "Make sure your server version is one of the following: {}".format(self.__valid_versions)
            return False
        if self.__version == "4.0.0" and self.__build_number is None:
            print "You need to specify a build number for server version"
            return False
        return True


def install_couchbase_server(couchbase_server_config):

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

    parser.add_option("", "--build-number",
                      action="store", type="string", dest="build_number", default=None,
                      help="server build to download")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    server_config = CouchbaseServerConfig(
        version=opts.version,
        build_number=opts.build_number,
    )

    install_couchbase_server(server_config)
