import json
import ConfigParser


class CustomConfigParser(ConfigParser.RawConfigParser):
    """Virtually identical to the original method, but delimit keys and values with '=' instead of ' = '
       Python 3 has a space_around_delimiters=False option for write, it does not work for python 2.x
    """
    def write(self, fp):
        DEFAULTSECT = "DEFAULT"
        """Write an .ini-format representation of the configuration state."""
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


def enable_cbs_ssl_in_cluster_config(cluster_config):
    # Write ssl_enabled = True in the cluster_config.json
    cluster_config_json = "{}.json".format(cluster_config)
    with open(cluster_config_json, "rw") as f:
        cluster = json.loads(f.read())

    cluster["cbs_ssl_enabled"] = True
    with open(cluster_config_json, "w") as f:
        json.dump(cluster, f, indent=4)

    # Write [cbs_ssl] cbs_ssl_enabled = True in the cluster_config
    config = CustomConfigParser()
    config.read(cluster_config)
    if not config.has_section("cbs_ssl"):
        config.add_section("cbs_ssl")
    config.set('cbs_ssl', 'cbs_ssl_enabled', 'True')

    with open(cluster_config, 'w') as f:
        config.write(f)


def disable_cbs_ssl_in_cluster_config(cluster_config):
    # Write ssl_enabled = False in the cluster_config.json
    # if ssl_enabled is present
    cluster_config_json = "{}.json".format(cluster_config)
    with open(cluster_config_json, "rw") as f:
        cluster = json.loads(f.read())
    f.close()

    if "cbs_ssl_enabled" in cluster:
        cluster["cbs_ssl_enabled"] = False
        with open(cluster_config_json, "w") as f:
            json.dump(cluster, f, indent=4)
        f.close()

    # Write [cbs_ssl] cbs_ssl_enabled = False in the cluster_config
    # if cbs_ssl is present
    config = CustomConfigParser()
    config.read(cluster_config)
    if config.has_section("cbs_ssl"):
        config.set('cbs_ssl', 'cbs_ssl_enabled', 'False')

        with open(cluster_config, 'w') as f:
            config.write(f)


def is_cbs_ssl_enabled(cluster_config):
    if ".json" not in cluster_config:
        cluster_config = "{}.json".format(cluster_config)

    with open(cluster_config) as f:
        cluster = json.loads(f.read())

    if "cbs_ssl_enabled" in cluster and cluster["cbs_ssl_enabled"]:
        return True

    return False
