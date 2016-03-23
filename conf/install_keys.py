import os
import subprocess
import sys

import ansible.inventory

from optparse import OptionParser

def install_keys(key_name, user_name):

    hostfile = os.environ["CLUSTER_CONFIG"]
    inv = ansible.inventory.Inventory(host_list=hostfile)
    hosts = inv.get_hosts()

    ips = []
    for host in hosts:
        host_vars = host.get_variables()
        ips.append(host_vars["ansible_host"])

    print("Are you sure you would like to copy public key '{0}' to vms: {1}".format(
        key_name, ips
    ))

    validate = raw_input("Enter 'y' to continue or 'n' to exit: ")
    if validate != "y":
        print("Exiting...")
        sys.exit(1)

    print("Using ssh-copy-id...")
    for ip in ips:
        subprocess.call([
            "ssh-copy-id", "-i", "{0}/.ssh/{1}".format(os.environ["HOME"], key_name),
            "{0}@{1}".format(user_name, ip)
        ])

    split_key = key_name.split(".")
    private_key = split_key[0]

    print("Add '{0}' to you ssh agent?".format(private_key))
    validate = raw_input("Enter 'y' to continue or 'n' to exit: ")
    if validate != "y":
        print("Exiting...")
        sys.exit(1)
    else:
        subprocess.call((["ssh-add", "{0}/.ssh/{1}".format(os.environ["HOME"], private_key)]))

if __name__ == "__main__":

    usage = "usage: install-keys.py --key-name=<name_of_key> --ssh-user=<user>"
    parser = OptionParser(usage=usage)

    parser.add_option(
        "", "--key-name",
        action="store",
        type="string",
        dest="key_name",
        help="ssh key to install to hosts",
        default=None
    )

    parser.add_option(
        "", "--ssh-user",
        action="store",
        type="string",
        dest="ssh_user",
        help="ssh key to install to hosts",
        default=None
    )

    cmd_args = sys.argv[1:]
    (opts, args) = parser.parse_args(cmd_args)

    if opts.key_name is None or opts.ssh_user is None:
        print(">>> Please provide --key-name=<key-name> AND --ssh-user=<user>")
        sys.exit(1)

    if opts.key_name is not None and not opts.key_name.endswith(".pub"):
        print(">>> Please provide a PUBLIC key (.pub) to install on the remote machines")
        sys.exit(1)

    install_keys(opts.key_name, opts.ssh_user)


