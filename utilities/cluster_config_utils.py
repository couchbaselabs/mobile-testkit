import configparser
import json
import os
import re

from keywords.exceptions import ProvisioningError
from shutil import copyfile, rmtree, make_archive
from subprocess import Popen, PIPE
from distutils.dir_util import copy_tree


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
                       "delta_sync_enabled", "x509_certs"]
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
            f.write("IP.{} = {}\n".format(item + 1, cbs_nodes[item]))
    cmd = ["./gen_keystore.sh", cbs_nodes[0], bucket_name[0]]
    print(" ".join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    print(stdout, stderr)

    # zipping the certificates
    os.chdir(curr_dir)
    make_archive("certs", "zip", certs_dir)

    for node in cluster["sync_gateways"]:
        if sg_platform.lower() != "macos" and sg_platform.lower() != "windows":
            cmd = ["scp", "certs.zip", "{}@{}:/tmp".format(username, node["ip"])]
        else:
            cmd = ["cp", "certs.zip", "/tmp"]
        print(" ".join(cmd))
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if stdout or stderr:
            print(stdout, stderr)


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

    num_lbs = len(cluster["load_balancers"])
    if num_lbs != 1:
        raise ProvisioningError("Expecting exactly 1 load balancer IP in {}".format(cluster_config))

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
