import os
from keywords.ClusterKeywords import ClusterKeywords
from keywords.utils import log_info
from keywords.constants import NGINX_BASIC_AUTH_FILE_LINUX
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_load_balancer_with_two_clusters_enabled
from utilities.cluster_config_utils import load_cluster_config_json, get_sg_platform


def install_nginx(cluster_config, customize_proxy=False, userName=None, password=None, base_url=None):
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
    sg_platform = get_sg_platform(cluster_config)
    extra_vars = initialize_extra_vars(cluster_config)
    if "debian" in sg_platform.lower():
        extra_vars["ansible_python_interpreter"] = "/usr/bin/python3"
        extra_vars["ansible_distribution"] = "Debian"
        extra_vars["ansible_os_family"] = "Linux"
    if userName is not None:
        extra_vars["user_auth_basic"] = "\"Authentication Required\""
        extra_vars["proxy_user_name"] = userName
        extra_vars["proxy_password"] = password
    if base_url is not None:
        extra_vars["config"] = "nginx_proxy.conf.j2"
        extra_vars["upstream_cbl"] = "server " + base_url.replace("http://", "") + ";"
        extra_vars["sync_gateway_url_resolver"] = topology["sync_gateways"][0].replace("http://", "")
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

        extra_vars["upstream_sync_gatways"] = upstream_definition
        extra_vars["upstream_sync_gatways_admin"] = upstream_definition_admin

        status = ansible_runner.run_ansible_playbook(
            "install-nginx.yml",
            extra_vars=extra_vars,
            subset=lb_names[0]
        )
        assert status == 0, "Failed to install nginx! on lb1"

        extra_vars["upstream_sync_gatways"] = upstream_definition2
        extra_vars["upstream_sync_gatways_admin"] = upstream_definition_admin2
        status = ansible_runner.run_ansible_playbook(
            "install-nginx.yml",
            extra_vars=extra_vars,
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

        extra_vars["upstream_sync_gatways"] = upstream_definition
        extra_vars["upstream_sync_gatways_admin"] = upstream_definition_admin

        if customize_proxy:
            extra_vars["keepalive_timeout"] = "keepalive_timeout 60s 60s;"
            extra_vars["proxy_send_timeout"] = "proxy_send_timeout 60s;"
            extra_vars["proxy_read_timeout"] = "proxy_read_timeout 60s;"
            extra_vars["proxy_socket_keepalive"] = "proxy_socket_keepalive on;"
            status = ansible_runner.run_ansible_playbook(
                "install-nginx.yml",
                extra_vars=extra_vars
            )
        else:
            status = ansible_runner.run_ansible_playbook(
                "install-nginx.yml",
                extra_vars=extra_vars
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
    extra_vars = initialize_extra_vars(cluster_config)

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

    extra_vars["upstream_sync_gatways"] = upstream_definition1
    extra_vars["upstream_sync_gatways_admin"] = upstream_definition_admin1

    status = ansible_runner.run_ansible_playbook(
        "install-nginx.yml",
        extra_vars=extra_vars,
        subset=lbs[0]
    )
    extra_vars["upstream_sync_gatways"] = upstream_definition2
    extra_vars["upstream_sync_gatways_admin"] = upstream_definition_admin2
    status = ansible_runner.run_ansible_playbook(
        "install-nginx.yml",
        extra_vars=extra_vars,
        subset=lbs[1]
    )

    assert status == 0, "Failed to install nginx!"


if __name__ == "__main__":
    usage = """usage: python libraries/provision/install_nginx.py"""

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_nginx(cluster_conf)


def initialize_extra_vars(cluster_config):
    sg_platform = get_sg_platform(cluster_config)
    ansible_distribution = sg_platform.capitalize()
    extra_vars = {
        "ansible_distribution": ansible_distribution
    }
    if "debian" in sg_platform.lower():
        extra_vars["ansible_python_interpreter"] = "/usr/bin/python3"

    return extra_vars
