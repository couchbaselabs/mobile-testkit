import os
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_load_balancer_with_two_clusters_enabled
from utilities.cluster_config_utils import load_cluster_config_json


def install_nginx(cluster_config, customize_proxy=False):
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

    cluster = ClusterKeywords(cluster_config)
    # Set lb_enable to False to get the actual SG IPs for nginx.conf
    topology = cluster.get_cluster_topology(cluster_config, lb_enable=False)

    # Get sync_gateway enpoints from cluster_config
    #  and build a string of upstream server definitions
    # upstream sync_gateway {
    #   server 192.168.33.11:4984;
    #   server 192.168.33.12:4984;
    #  }
    upstream_definition = ""
    upstream_definition_admin = ""
    ansible_runner = AnsibleRunner(cluster_config)

    if is_load_balancer_with_two_clusters_enabled(cluster_config):
        upstream_definition2 = ""
        upstream_definition_admin2 = ""
        count = 0
        lb_names = []

        cluster_json = load_cluster_config_json(cluster_config)
        for lb in cluster_json["load_balancers"]:
            lb_names.append(lb["name"])

        total_cluster_nodes = cluster_json["environment"]["sgw_cluster1_count"] + cluster_json["environment"]["sgw_cluster2_count"]
        for sg in topology["sync_gateways"]:
            # string http:// to adhere to expected format for nginx.conf
            if count < cluster_json["environment"]["sgw_cluster1_count"]:
                ip_port = sg["public"].replace("http://", "")
                ip_port_admin = sg["admin"].replace("http://", "")
                upstream_definition += "server {};\n".format(ip_port)
                upstream_definition_admin += "server {};\n".format(ip_port_admin)
            elif count < total_cluster_nodes:
                ip_port = sg["public"].replace("http://", "")
                ip_port_admin = sg["admin"].replace("http://", "")
                upstream_definition2 += "server {};\n".format(ip_port)
                upstream_definition_admin2 += "server {};\n".format(ip_port_admin)
            count += 1
        log_info("Upstream definition: {}".format(upstream_definition))
        log_info("Upstream definition admin: {}".format(upstream_definition_admin))
        log_info("Upstream definition: {}".format(upstream_definition2))
        log_info("Upstream definition admin: {}".format(upstream_definition_admin2))
        status = ansible_runner.run_ansible_playbook(
            "install-nginx.yml",
            extra_vars={
                "upstream_sync_gatways": upstream_definition,
                "upstream_sync_gatways_admin": upstream_definition_admin
            },
            subset=lb_names[0]
        )
        assert status == 0, "Failed to install nginx! on lb1"

        status = ansible_runner.run_ansible_playbook(
            "install-nginx.yml",
            extra_vars={
                "upstream_sync_gatways": upstream_definition2,
                "upstream_sync_gatways_admin": upstream_definition_admin2
            },
            subset=lb_names[1]
        )

        assert status == 0, "Failed to install nginx on lb2!"
    else:
        for sg in topology["sync_gateways"]:
            # string http:// to adhere to expected format for nginx.conf
            ip_port = sg["public"].replace("http://", "")
            ip_port_admin = sg["admin"].replace("http://", "")
            upstream_definition += "server {};\n".format(ip_port)
            upstream_definition_admin += "server {};\n".format(ip_port_admin)

        log_info("Upstream definition: {}".format(upstream_definition))
        log_info("Upstream definition admin: {}".format(upstream_definition_admin))

        if customize_proxy:
            status = ansible_runner.run_ansible_playbook(
                "install-nginx.yml",
                extra_vars={
                    "upstream_sync_gatways": upstream_definition,
                    "upstream_sync_gatways_admin": upstream_definition_admin,
                    "proxy_send_timeout": "proxy_send_timeout 60s;",
                    "proxy_read_timeout": "proxy_read_timeout 60s;",
                    "proxy_socket_keepalive": "proxy_socket_keepalive on;"
                }
            )
        else:
            status = ansible_runner.run_ansible_playbook(
                "install-nginx.yml",
                extra_vars={
                    "upstream_sync_gatways": upstream_definition,
                    "upstream_sync_gatways_admin": upstream_definition_admin
                }
            )

        assert status == 0, "Failed to install nginx! on lb1"


def install_nginx_for_2_sgw_clusters(cluster_config, cluster1_nodes=2, cluster2_nodes=2):
    """
    Deploys nginx to nodes with the load_balancer tag for two sgw cluster

    1. Get the sync_gateway endpoints from the cluster configuration
    2. Use the endpoints to render the nginx config (resources/nginx_configs/nginx.conf)
      to distribute load across the running sync_gateways.
      i.e. If your 'cluster_config' has 2 sync_gateways, nginx will be setup to forward
        requests to both of the sync_gateways using a weighted round robin distribution.
        If you have 3, it will split the load between 3, etc ...
    3. Deploy the config and install nginx on load_balancer nodes
    4. Start the nginx service
    """

    cluster = ClusterKeywords(cluster_config)
    # Set lb_enable to False to get the actual SG IPs for nginx.conf
    topology = cluster.get_cluster_topology(cluster_config, lb_enable=False)
    lbs = []

    upstream_definition1 = ""
    upstream_definition_admin1 = ""
    upstream_definition2 = ""
    upstream_definition_admin2 = ""
    count = 0
    total_cluster_nodes = topology["environment"]["sgw_cluster1_count"] + topology["environment"]["sgw_cluster2_count"]
    for sg in topology["sync_gateways"]:
        # string http:// to adhere to expected format for nginx.conf
        if count < topology["environment"]["sgw_cluster1_count"]:
            ip_port = sg["public"].replace("http://", "")
            ip_port_admin = sg["admin"].replace("http://", "")
            upstream_definition1 += "server {};\n".format(ip_port)
            upstream_definition_admin1 += "server {};\n".format(ip_port_admin)
        elif count < total_cluster_nodes:
            ip_port = sg["public"].replace("http://", "")
            ip_port_admin = sg["admin"].replace("http://", "")
            upstream_definition2 += "server {};\n".format(ip_port)
            upstream_definition_admin2 += "server {};\n".format(ip_port_admin)
        count += 1

    log_info("Upstream definition: {}".format(upstream_definition1))
    log_info("Upstream definition admin: {}".format(upstream_definition_admin1))
    log_info("Upstream definition: {}".format(upstream_definition2))
    log_info("Upstream definition admin: {}".format(upstream_definition_admin2))

    ansible_runner = AnsibleRunner(cluster_config)
    for lb in topology["load_balancers"]:
        lbs.append(lb.replace("http://", ""))

    status = ansible_runner.run_ansible_playbook(
        "install-nginx.yml",
        extra_vars={
            "upstream_sync_gatways": upstream_definition1,
            "upstream_sync_gatways_admin": upstream_definition_admin1,
        },
        subset=lbs[0]
    )

    status = ansible_runner.run_ansible_playbook(
        "install-nginx.yml",
        extra_vars={
            "upstream_sync_gatways": upstream_definition2,
            "upstream_sync_gatways_admin": upstream_definition_admin2
        },
        subset=lbs[1]
    )

    assert status == 0, "Failed to install nginx!"


if __name__ == "__main__":
    usage = """usage: python libraries/provision/install_nginx.py"""

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_nginx(cluster_conf)
