import os

from ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from keywords.utils import log_info

# Install aws credentials onto machine in /root/.aws/credentials file.
# Currently used by awslogs, which is a cloudwatch logs forwarder.

def install_aws_credentials(cluster_config):

    log_info("Installing aws credentials for cluster_config: {}".format(cluster_config))

    ansible_runner = AnsibleRunner(config=cluster_config)

    status = ansible_runner.run_ansible_playbook(
        "install-aws-credentials.yml",
        extra_vars={
            "aws_access_key_id": "foo",
            "aws_secret_access_key": "bar",
        },
    )
    if status != 0:
        raise ProvisioningError("Failed to aws credentials")


if __name__ == "__main__":
    usage = "usage: python install_aws_credentials.py"

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_aws_credentials(cluster_conf)
