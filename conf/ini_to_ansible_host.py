import sys
import os
import ConfigParser

from optparse import OptionParser
import install_keys


def ini_file_to_dictionary(ini_file):

    ini_abs_path = os.path.abspath(ini_file)
    if not os.path.isfile(ini_abs_path):
        print("Could not find .ini file: {}".format(ini_abs_path))
        sys.exit(1)

    print("Converting .ini: {}".format(ini_abs_path))

    config = ConfigParser.ConfigParser()
    config.read(ini_abs_path)
    print(config.sections())

    section_options = {}
    for section in config.sections():
        opts = {}
        options = config.options(section)
        for option in options:
            opts[option] = config.get(section, option)
        section_options[section] = opts
    return section_options


def copy_keys(cbs, sgs, key_name):
    ips = [i["ip"] for i in cbs]
    ips.extend([i["ip"] for i in sgs])
    install_keys.install_keys(key_name, "root", ips)


def ini_to_ansible_host(ini_file, key_name=None):

    print(">>> Using .ini file: {}".format(ini_file))

    if key_name is not None:
        print(">>> Installing key: {}".format(key_name))

    ini_dict = ini_file_to_dictionary(ini_file)

    host_file = []
    cbs = []
    sgs = []

    for cb in ini_dict["couchbase_servers"]:
        vm = ini_dict["couchbase_servers"][cb]
        ip = ini_dict["vms"][vm]
        cbs.append({"name": cb, "ip": ip})
        host_entry = "{0} ansible_ssh_host={1}\n".format(
            cb, ip
        )
        host_file.append(host_entry)

    for sg in ini_dict["sync_gateways"]:
        vm = ini_dict["sync_gateways"][sg]
        ip = ini_dict["vms"][vm]
        sgs.append({"name": sg, "ip": ip})
        host_entry = "{0} ansible_ssh_host={1}\n".format(
            sg, ip,
        )
        host_file.append(host_entry)

    host_file.append("\n")

    if key_name is not None:
        print("Installing key...")
        copy_keys(cbs, sgs, key_name)

    host_file.append("[couchbase_servers]\n")
    for cb in cbs:
        host_file.append("{}\n".format(cb["name"]))

    host_file.append("\n")

    host_file.append("[sync_gateways]\n")
    for sg in sgs:
        host_file.append("{}\n".format(sg["name"]))

    # generate host file
    host_file_test = "".join(host_file)
    with open("temp_ansible_hosts", "w") as hosts:
        hosts.write(host_file_test)

    # export INVENTORY env variable
    return sgs, cbs

if __name__ == "__main__":

    usage = "usage: ini_to_ansible_host.py --ini-file=<absolute_path_to_ini_file> --install-keys=<name_of_public_key>"
    parser = OptionParser(usage=usage)

    parser.add_option(
        "", "--ini-file",
        action="store",
        type="string",
        dest="ini_file",
        help=".ini file to define cluster",
        default=""
    )

    parser.add_option(
        "", "--install-keys",
        action="store",
        type="string",
        dest="key_to_install",
        help="public ssh key to install",
        default=None
    )

    cmd_args = sys.argv[1:]
    (opts, args) = parser.parse_args(cmd_args)

    ini_to_ansible_host(opts.ini_file, opts.key_to_install)
