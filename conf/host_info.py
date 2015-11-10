import sys
import os
import ConfigParser


def ini_file_to_dictionary(ini_file):
    ini_abs_path = os.path.abspath(ini_file)
    if not os.path.isfile(ini_abs_path):
        print("Could not find .ini file: {}".format(ini_abs_path))
        sys.exit(1)

    config = ConfigParser.ConfigParser()
    config.read(ini_abs_path)

    section_options = {}
    for section in config.sections():
        opts = {}
        options = config.options(section)
        for option in options:
            opts[option] = config.get(section, option)
        section_options[section] = opts
    return section_options


def get_host_info(ini_file):

    ini_dict = ini_file_to_dictionary(ini_file)

    cbs = []
    sgs = []

    for cb in ini_dict["couchbase_servers"]:
        vm = ini_dict["couchbase_servers"][cb]
        ip = ini_dict["vms"][vm]
        cbs.append({"name": cb, "ip": ip})

    for sg in ini_dict["sync_gateways"]:
        vm = ini_dict["sync_gateways"][sg]
        ip = ini_dict["vms"][vm]
        sgs.append({"name": sg, "ip": ip})

    return sgs, cbs
