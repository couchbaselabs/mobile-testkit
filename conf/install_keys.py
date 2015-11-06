import os
import subprocess
import sys


def install_keys(key_name, user_name, ips):

    if not key_name or not user_name:
        print("Make sure to specify a public key with --key-name and user with --remote-user")
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

    split_key = key_name.split(".")
    private_key = split_key[0]

    print("Add '{0}' to you ssh agent?".format(private_key))
    validate = raw_input("Enter 'y' to continue or 'n' to exit: ")
    if validate != "y":
        print("Exiting...")
        sys.exit(1)
    else:
        subprocess.call((["ssh-add", "{0}/.ssh/{1}".format(os.environ["HOME"], private_key)]))

