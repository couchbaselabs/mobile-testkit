import ConfigParser
import json
from keywords.exceptions import ProvisioningError
from shutil import copyfile


class CustomConfigParser(ConfigParser.RawConfigParser):
    """Virtually identical to the original method, but delimit keys and values with '=' instead of ' = '
       Python 3 has a space_around_delimiters=False option for write, it does not work for python 2.x
    """
    def write(self, fp):

        DEFAULTSECT = "DEFAULT"

        # Write an .ini-format representation of the configuration state.
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
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
        valid_props = ["cbs_ssl_enabled", "xattrs_enabled", "sg_lb_enabled", "sync_gateway_version", "server_version", "no_conflicts_enabled"]
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


def get_sg_version(cluster_config):
    """ Loads cluster config to get sync gateway version"""
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["sync_gateway_version"]


def no_conflicts_enabled(cluster_config):
    "Get no conflicts value from cluster config"
    cluster = load_cluster_config_json(cluster_config)
    try:
        return cluster["environment"]["no_conflicts_enabled"]
    except KeyError:
        return False


def get_revs_limit(cluster_config):
    "Get revs limit"
    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["revs_limit"]


def copy_to_temp_conf(cluster_config, mode):
    # Creating temporary cluster config and json files to add revs limit dynamically
    temp_cluster_config = "resources/cluster_configs/temp_cluster_config_{}".format(mode)
    temp_cluster_config_json = "resources/cluster_configs/temp_cluster_config_{}.json".format(mode)
    cluster_config_json = "{}.json".format(cluster_config)
    open(temp_cluster_config, "w+")
    open(temp_cluster_config_json, "w+")
    copyfile(cluster_config, temp_cluster_config)
    copyfile(cluster_config_json, temp_cluster_config_json)
    return temp_cluster_config
