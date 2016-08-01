import sys
import os

from optparse import OptionParser

from keywords.ClusterKeywords import ClusterKeywords
from ansible_runner import AnsibleRunner


def install_nginx(cluster_config):

    cluster = ClusterKeywords()
    topology = cluster.get_cluster_topology(cluster_config)

    print(topology)


    #
    # if not sync_gateway_config.is_valid():
    #     print "Invalid sync_gateway provisioning configuration. Exiting ..."
    #     sys.exit(1)
    #
    # if sync_gateway_config.build_flags != "":
    #     print("\n\n!!! WARNING: You are building with flags: {} !!!\n\n".format(sync_gateway_config.build_flags))
    #
    # ansible_runner = AnsibleRunner()
    # config_path = os.path.abspath(sync_gateway_config.config_path)
    #
    # sync_gateway_config.commit is not None:
    #     # Install source
    #     status = ansible_runner.run_ansible_playbook(
    #         "install-sync-gateway-source.yml",
    #         extra_vars={
    #             "sync_gateway_config_filepath": config_path,
    #             "commit": sync_gateway_config.commit,
    #             "build_flags": sync_gateway_config.build_flags,
    #             "skip_bucketflush": sync_gateway_config.skip_bucketflush
    #         }
    #     )
    #     assert status == 0, "Failed to install sync_gateway source"



if __name__ == "__main__":
    usage = """usage: python libraries/provision/install_nginx.py"""

    default_sync_gateway_config = os.path.abspath("resources/nginx/2sg")

    parser = OptionParser(usage=usage)

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_nginx(cluster_config)

