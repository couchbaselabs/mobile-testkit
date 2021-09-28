import configparser
import json
import os
import re
from datetime import timedelta
from keywords.exceptions import ProvisioningError
from shutil import copyfile, rmtree
from subprocess import Popen, PIPE
from distutils.dir_util import copy_tree
from couchbase.cluster import PasswordAuthenticator, ClusterTimeoutOptions, ClusterOptions, Cluster
from keywords.constants import BUCKET_LIST


class CustomConfigParser(configparser.RawConfigParser):
    """Virtually identical to the original method, but delimit keys and values with '=' instead of ' = '
       Python 3 has a space_around_delimiters=False option for write, it does not work for python 2.x
    """

    def write(self, fp):

        DEFAULTSECT = "DEFAULT"

        # Write an .ini-format representation of the configuration state.
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in list(self._defaults.items()):
                fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in list(self._sections[section].items()):
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = "=".join((key, str(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")


def get_cluster(url, bucket_name):
    timeout_options = ClusterTimeoutOptions(kv_timeout=timedelta(seconds=30), query_timeout=timedelta(seconds=300))
    options = ClusterOptions(PasswordAuthenticator("Administrator", "password"), timeout_options=timeout_options)
    cluster = Cluster(url, options)
    cluster = cluster.bucket(bucket_name)
    return cluster.default_collection()


def persist_cluster_config_environment_prop(cluster_config, property_name, value, property_name_check=True):
    """ Loads the cluster_config and sets

    [environment]
    property_name=value

    for cluster_config and

    "property_name": value

    for cluster_config.json
    """

    if property_name_check is True:
        valid_props = ["cbs_ssl_enabled", "xattrs_enabled", "sg_lb_enabled", "sync_gateway_version", "server_version",
                       "no_conflicts_enabled", "sync_gateway_ssl", "sg_use_views", "number_replicas",
                       "delta_sync_enabled", "x509_certs", "hide_product_version", "cbs_developer_preview", "disable_persistent_config",
                       "server_tls_skip_verify", "disable_tls_server", "disable_admin_auth"]
        if property_name not in valid_props:
            raise ProvisioningError("Make sure the property you are trying to change is one of: {}".format(valid_props))

    # Write property = value in the cluster_config.json
    cluster_config_json = "{}.json".format(cluster_config)
    with open(cluster_config_json) as f:
        cluster = json.loads(f.read())

    cluster["environment"][property_name] = value
    with open(cluster_config_json, "w") as f:
        json.dump(cluster, f, indent=4)

    # Write [section] property = value in the cluster_config
    config = CustomConfigParser()
    config.read(cluster_config)
    config.set('environment', property_name, str(value))

    with open(cluster_config, 'w') as f:
        config.write(f)


def generate_x509_certs(cluster_config, bucket_name, sg_platform):
    ''' Generate and insert x509 certs for CBS and SG TLS Handshake'''
    cluster = load_cluster_config_json(cluster_config)
    if sg_platform.lower() != "windows" and sg_platform.lower() != "macos":
        for line in open("ansible.cfg"):
            match = re.match('remote_user\s*=\s*(\w*)$', line)
            if match:
                username = match.groups()[0].strip()
                print(username)
                break
    curr_dir = os.getcwd()
    certs_dir = os.path.join(curr_dir, "certs")
    if os.path.exists(certs_dir):
        rmtree(certs_dir)
    os.mkdir(certs_dir)

    # Copying files to generate certs
    src = os.path.join(curr_dir, "resources/x509_cert_gen")
    copy_tree(src, certs_dir)
    os.chdir(certs_dir)
    cbs_nodes = [node["ip"] for node in cluster["couchbase_servers"]]

    with open("openssl-san.cnf", "a+") as f:
        for item in range(len(cbs_nodes)):
            if "couchbase" not in cbs_nodes[item]:
                f.write("IP.{} = {}\n".format(item + 1, cbs_nodes[item]))
            else:
                f.write("DNS.{} = {}\n".format(item + 1, cbs_nodes[item]))

    cmd = ["./gen_keystore.sh", cbs_nodes[0], bucket_name[0]]
    print(" ".join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    print(stdout, stderr)

    os.chdir(curr_dir)


def load_cluster_config_json(cluster_config):
    """ Load json version of cluster config """

    if ".json" not in cluster_config:
        cluster_config = "{}.json".format(cluster_config)

    with open(cluster_config) as f:
        cluster = json.loads(f.read())

    return cluster


def is_cbs_ssl_enabled(cluster_config):
    """ Loads cluster config to see if cbs ssl is enabled """

    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["cbs_ssl_enabled"]


def is_x509_auth(cluster_config):
    ''' Load cluster config to see if auth should be done using x509 certs '''
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["x509_certs"]


def get_cbs_servers(cluster_config):
    """ Loads cluster config to see if cbs ssl is enabled """
    cluster = load_cluster_config_json(cluster_config)
    cbs_ips = [cb["ip"] for cb in cluster["couchbase_servers"]]
    return cbs_ips


def is_xattrs_enabled(cluster_config):
    """ Loads cluster config to see if cbs ssl is enabled """

    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["xattrs_enabled"]


def is_load_balancer_enabled(cluster_config):
    """ Loads cluster config to see if load balancer is enabled """
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["sg_lb_enabled"]


def get_load_balancer_ip(cluster_config):
    """ Loads cluster config to fetch load balancer ip """
    cluster = load_cluster_config_json(cluster_config)

    lb_ip = cluster["load_balancers"][0]["ip"]
    return lb_ip


def get_sg_replicas(cluster_config):
    """ Loads cluster config to get sync gateway version"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["number_replicas"]


def get_sg_use_views(cluster_config):
    """ Loads cluster config to get sync gateway views/GSI"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["sg_use_views"]


def is_ipv6(cluster_config):
    """ Loads cluster config to get IPv6 status"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["ipv6_enabled"]


def get_cbs_primary_nodes_str(cluster_config, cbs_nodes):
    """Parse the cluster node string and reformat it according to IP config of nodes
    for IPv4 - 10.0.0.1,10.0.0.2 --> 10.0.0.1,10.0.0.1
    for IPv6 - fc00::11,fc00::12 --> [fc00::11],[fc00::12]
    """
    if is_ipv6(cluster_config):
        if ',' in cbs_nodes:
            node_str = ""
            for node in cbs_nodes.split(','):
                node_str = node_str + "[{}],".format(node)
            cbs_nodes = node_str.rstrip(",")
            return cbs_nodes
        else:
            return "[{}]".format(cbs_nodes)
    else:
        return cbs_nodes


def get_sg_version(cluster_config):
    """ Loads cluster config to get sync gateway version"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["sync_gateway_version"]


def get_cbs_version(cluster_config):
    """ Loads cluster config to get the couchbase server version"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["server_version"]


def no_conflicts_enabled(cluster_config):
    "Get no conflicts value from cluster config"
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["no_conflicts_enabled"]
    except KeyError:
        return False


def sg_ssl_enabled(cluster_config):
    "Get SG SSL value from cluster config"
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["sync_gateway_ssl"]
    except KeyError:
        return False


def get_revs_limit(cluster_config):
    "Get revs limit"
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["revs_limit"]


def get_redact_level(cluster_config):
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["redactlevel"]


def get_sg_platform(cluster_config):
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["sg_platform"]


def is_delta_sync_enabled(cluster_config):
    """ Loads cluster config to see if delta sync is enabled """

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["delta_sync_enabled"]
    except KeyError:
        return False


def is_cbs_ce_enabled(cluster_config):
    """ returns if true if CBS CE is enabled otherwise false """
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["cbs_ce"]
    except KeyError:
        return False


def is_magma_enabled(cluster_config):
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["magma_storage_enabled"]
    except KeyError:
        return False


def copy_to_temp_conf(cluster_config, mode):
    # Creating temporary cluster config and json files to add configuration dynamically
    temp_cluster_config = "resources/cluster_configs/temp_cluster_config_{}".format(mode)
    temp_cluster_config_json = "resources/cluster_configs/temp_cluster_config_{}.json".format(mode)
    cluster_config_json = "{}.json".format(cluster_config)
    open(temp_cluster_config, "w+")
    open(temp_cluster_config_json, "w+")
    copyfile(cluster_config, temp_cluster_config)
    copyfile(cluster_config_json, temp_cluster_config_json)
    return temp_cluster_config


def copy_sgconf_to_temp(sg_conf, mode):
    temp_sg_conf_name = "temp_sg_config"
    temp_sg_config = "resources/sync_gateway_configs/temp_sg_config_{}.json".format(mode)
    open(temp_sg_config, "w+")
    copyfile(sg_conf, temp_sg_config)
    bucket_list = []
    if "sync_gateway_configs_cpc" in sg_conf:
        bucket_list = get_bucket_list_cpc(sg_conf)
    return temp_sg_config, temp_sg_conf_name, bucket_list


def copy_sgconf_to_tempconfig_for_reset_method(sg_conf, mode):
    temp_sg_conf_name = "temp_sg_config"
    temp_sg_config = "resources/sync_gateway_configs/temp_sg_config_reset_{}.json".format(mode)
    open(temp_sg_config, "w+")
    copyfile(sg_conf, temp_sg_config)
    return temp_sg_config, temp_sg_conf_name


def replace_string_on_sgw_config(sg_conf, replace_string, new_string):
    with open(sg_conf, 'r') as file:
        filedata = file.read()
    filedata = filedata.replace(replace_string, new_string)
    with open(sg_conf, 'w') as file:
        file.write(filedata)
    return sg_conf


def is_load_balancer_with_two_clusters_enabled(cluster_config):
    """ Loads cluster config to see if load balancer is enabled """
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["two_sg_cluster_lb_enabled"]
    except KeyError:
        return False


def is_hide_prod_version_enabled(cluster_config):
    """ Loads cluster config to see if hide_prod_version is enabled """

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["hide_product_version"]
    except KeyError:
        return False


def is_centralized_persistent_config_disabled(cluster_config):
    """ verify centralized persistent config enabled/disabled"""

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["disable_persistent_config"]
    except KeyError:
        return False


def copy_json_to_temp_file(conf, temp_config="resources/temp/temp_config.json"):
    config_path = os.path.abspath(temp_config)
    file = open(config_path, "w+")
    file.write(json.dumps(conf, indent=4))
    file.close
    return temp_config


def get_bucket_list_cpc(sgw_config):
    sgw_conf_file_name = sgw_config.split('/')[-1].split("_cc.")[0]
    bucket_list_data = open(BUCKET_LIST)
    json_data = json.load(bucket_list_data)
    return json_data[sgw_conf_file_name]


def is_server_tls_skip_verify_enabled(cluster_config):
    """ verify server tls skip verify config enabled/disabled"""

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["server_tls_skip_verify"]
    except KeyError:
        return False


def is_tls_server_disabled(cluster_config):
    """ verify tls server enabled/disabled"""

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["disable_tls_server"]
    except KeyError:
        return False


def is_admin_auth_disabled(cluster_config):
    """ verify admin auth enabled/disabled"""

    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["disable_admin_auth"]
    except KeyError:
        return False
