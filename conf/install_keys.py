import os
import subprocess
import sys


def check_vms_online(ips):

    reachable_vms = []
    unreachable_vms = []

    for ip in ips:
        ping_response = os.system("ping -c 1 {}".format(ip))
        if ping_response == 0:
            reachable_vms.append(ip)
        else:
            unreachable_vms.append(ip)

    return reachable_vms, unreachable_vms


def install_keys(key_name, user_name, ips):

    if not key_name or not user_name:
        print("Make sure to specify a public key with --key-name and user with --remote-user")
        sys.exit(1)

    reachable_vms, unreachable_vms = check_vms_online(ips)

    if len(reachable_vms) != len(ips) and len(reachable_vms) != 0:
        print("Could not ping each vm in the cluster: Unreachable {}".format(unreachable_vms))
        sys.exit(1)

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

    print("Add '{0}' to you ssh agent?".format(key_name))
    validate = raw_input("Enter 'y' to continue or 'n' to exit: ")
    if validate != "y":
        print("Exiting...")
        sys.exit(1)
    else:
        subprocess.call((["ssh-add", "{0}/.ssh/{1}".format(os.environ["HOME"], key_name)]))

