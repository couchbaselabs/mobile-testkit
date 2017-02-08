import os

from ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from keywords.utils import log_info

import argparse


# Install aws credentials onto machine in /root/.aws/credentials file.
# Currently used by awslogs, which is a cloudwatch logs forwarder.
#
# Don't use full aws credentials, create a keypair on the existing mobiletestkit user
# which has full cloudwatch permissions, but nothing else

def install_aws_credentials(cluster_config, aws_access_key_id, aws_secret_access_key):

    log_info("Installing aws credentials for cluster_config: {}".format(cluster_config))

    ansible_runner = AnsibleRunner(config=cluster_config)

    status = ansible_runner.run_ansible_playbook(
        "install-aws-credentials.yml",
        extra_vars={
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
        },
    )
    if status != 0:
        raise ProvisioningError("Failed to aws credentials")


if __name__ == "__main__":

    usage = "usage: python install_aws_credentials.py --aws-access-key-id AKIAIYOURKEY --aws-secret-access-key uaLqkyoursecret"

    parser = argparse.ArgumentParser()
    parser.add_argument("--aws-access-key-id", help="aws access key id (use limited key, see comments in code)", required=True)
    parser.add_argument("--aws-secret-access-key", help="aws secret access key", required=True)
    args = parser.parse_args()

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_aws_credentials(cluster_conf, args.aws_access_key_id, args.aws_secret_access_key)
