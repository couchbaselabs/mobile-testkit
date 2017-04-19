import ConfigParser
import json


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


def persist_cluster_config_environment_prop(cluster_config, property_name, value):
    """ Loads the cluster_config and sets

    [environment]
    property_name=value

    for cluster_config and

    "property_name": value

    for cluster_config.json
    """

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


def is_xattrs_enabled(cluster_config):
    """ Loads cluster config to see if cbs ssl is enabled """

    cluster = load_cluster_config_json(cluster_config)
    return cluster["environment"]["xattrs_enabled"]
