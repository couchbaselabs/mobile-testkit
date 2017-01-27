import os
import subprocess
import sys

from optparse import OptionParser
from subprocess import CalledProcessError

from generate_clusters_from_pool import get_hosts
import paramiko

def install_keys(key_path, user_name):

    hosts, _ = get_hosts()

    print("Deploying key '{0}' to vms: {1}".format(
        key_path, hosts
    ))

    key_data = open(os.path.expanduser(key_path)).read()

    for host in hosts:

        print("Deploying key to {}@{}".format(user_name, host))

        deploy_key(
            key_data,
            host,
            user_name,
            "",
        )


def deploy_key(key, server, username, password):

    if key is None or len(key) == 0:
        raise Exception("Empty key given, check key path")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # client.connect(server, username=username, password=password)
    # TODO: vagrant use case
    client.connect(server, username=username)
    client.exec_command('mkdir -p ~/.ssh/')
    client.exec_command('echo "%s" > ~/.ssh/authorized_keys' % key)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

if __name__ == "__main__":

    usage = "usage: install-keys.py --key-path=<name_of_key> --ssh-user=<user>"
    parser = OptionParser(usage=usage)

    parser.add_option(
        "", "--key-path",
        action="store",
        type="string",
        dest="key_path",
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

    if opts.key_path is None or opts.ssh_user is None:
        print(">>> Please provide --key-path=<key-path> AND --ssh-user=<user>")
        sys.exit(1)

    if opts.key_path is not None and not opts.key_path.endswith(".pub"):
        print(">>> Please provide a PUBLIC key (.pub) to install on the remote machines")
        sys.exit(1)

    install_keys(opts.key_path, opts.ssh_user)
