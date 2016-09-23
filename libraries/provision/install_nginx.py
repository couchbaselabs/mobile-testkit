import sys
import os

from optparse import OptionParser

from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info

from ansible_runner import AnsibleRunner


def install_nginx(cluster_config):
    """
    Deploys nginx to nodes with the load_balancer tag

    1. Get the sync_gateway endpoints from the cluster configuration
    2. Use the endpoints to render the nginx config (resources/nginx_configs/nginx.conf)
      to distribute load across the running sync_gateways.
      i.e. If your 'cluster_config' has 2 sync_gateways, nginx will be setup to forward
        requests to both of the sync_gateways using a weighted round robin distribution.
        If you have 3, it will split the load between 3, etc ...
    3. Deploy the config and install nginx on load_balancer nodes
    4. Start the nginx service
    """

    cluster = ClusterKeywords()
    topology = cluster.get_cluster_topology(cluster_config)

    # Get sync_gateway enpoints from cluster_config
    #  and build a string of upstream server definitions
    # upstream sync_gateway {
    #   server 192.168.33.11:4984;
    #   server 192.168.33.12:4984;
    #  }
    upstream_definition = ""
    for sg in topology["sync_gateways"]:
        # string http:// to adhere to expected format for nginx.conf
        ip_port = sg["public"].replace("http://", "")
        upstream_definition += "server {};\n".format(ip_port)

    log_info("Upstream definition: ")
    log_info(upstream_definition)

    ansible_runner = AnsibleRunner(cluster_config)
    status = ansible_runner.run_ansible_playbook(
        "install-nginx.yml",
        extra_vars={
            "upstream_sync_gatways": upstream_definition
        }
    )

    assert status == 0, "Failed to install nginx!"



if __name__ == "__main__":
    usage = """usage: python libraries/provision/install_nginx.py"""

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_nginx(cluster_conf)

