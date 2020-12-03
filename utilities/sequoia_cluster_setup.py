import argparse
import os

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.constants import CLUSTER_CONFIGS_DIR
from libraries.provision.ansible_runner import AnsibleRunner


def get_arguments_from_sequoia(parser):
    parser.add_argument("--cbs-hosts",
                        action="store",
                        help="couchbase server ip addresses, separated by comma")
    parser.add_argument("--sgw-hosts",
                        action="store",
                        help="sgw-host: the host ip for sync gateway server")
    parser.add_argument("--bucket-name",
                        action="store",
                        help="bucket-name: the bucket name that sync gateway pointing to")
    parser.add_argument("--bucket-user",
                        action="store",
                        help="bucket-user: the username to connect to the bucket on couchbase server")
    parser.add_argument("--bucket-user-pwd",
                        action="store",
                        help="bucket-user-pwd: the password for bucket-user")
    parser.add_argument("--server-scheme",
                        action="store",
                        default="http",
                        help="server-scheme: the protocal sync gateway connect to couchbase server")
    parser.add_argument("--server-port",
                        action="store",
                        default="8091",
                        help="server-port: the port where couchbase server is listening")
    return parser.parse_args()


def set_sync_gateway(bucket_user, bucket_user_pwd, bucket_name, server_scheme, server_port, cbs_hosts):
    cluster_config = "{}/base_cc".format(CLUSTER_CONFIGS_DIR)
    ansible_runner = AnsibleRunner(cluster_config)
    sg_config = sync_gateway_config_path_for_mode("sync_gateway_sequoia", "cc")
    config_path = os.path.abspath(sg_config)

    playbook_vars = {
        "sync_gateway_config_filepath": config_path,
        "username": bucket_user,
        "password": bucket_user_pwd,
        "server_port": server_port,
        "server_scheme": server_scheme,
        "couchbase_server_primary_node": cbs_hosts,
        "bucket_name": bucket_name,
        "x509_auth": False
    }

    status = ansible_runner.run_ansible_playbook(
        "deploy-sync-gateway-config-sequoia.yml",
        extra_vars=playbook_vars
    )


if __name__ == "__main__":
    # taking arguments from sequoia framework
    parser = argparse.ArgumentParser(description='Configure Sync Gateway as a component in Sequoia framework.')
    args = get_arguments_from_sequoia(parser)

    set_sync_gateway(args.bucket_user, args.bucket_user_pwd, args.bucket_name,
                     args.server_scheme, args.server_port, args.cbs_hosts)

    print("sync gateway config has been updated and service is up!")
