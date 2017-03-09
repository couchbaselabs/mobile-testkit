import os
import sys

from optparse import OptionParser

from generate_clusters_from_pool import get_hosts
import paramiko


def install_keys(public_key_path, user_name, ssh_password):

    hosts, _ = get_hosts()

    print("Deploying key '{0}' to vms: {1}".format(
        public_key_path, hosts
    ))

    public_key_data = open(os.path.expanduser(public_key_path)).read()

    for host in hosts:

        print("Deploying key to {}@{}".format(user_name, host))

        deploy_key(
            public_key_data,
            host,
            user_name,
            ssh_password,
        )


def deploy_key(public_key, server, username, password):

    if public_key is None or len(public_key) == 0:
        raise Exception("Empty key given, check key path")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if password == "":
        client.connect(server, username=username)
    else:
        client.connect(server, username=username, password=password)

    client.exec_command('mkdir -p ~/.ssh/')
    client.exec_command('echo "%s" > ~/.ssh/authorized_keys' % public_key)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

if __name__ == "__main__":

    usage = "usage: install-keys.py --public-key-path=<name_of_public_key> --ssh-user=<user>"
    parser = OptionParser(usage=usage)

    parser.add_option(
        "", "--public-key-path",
        action="store",
        type="string",
        dest="public_key_path",
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

    parser.add_option(
        "", "--ssh-password",
        action="store",
        type="string",
        dest="ssh_password",
        help="Password auth to login as ssh-user.  Ignore if you already have another public_key and can use passwordless auth",
        default=None
    )

    cmd_args = sys.argv[1:]
    (opts, args) = parser.parse_args(cmd_args)

    if opts.public_key_path is None or opts.ssh_user is None:
        print(">>> Please provide --public-key-path=<public-key-path> AND --ssh-user=<user>")
        sys.exit(1)

    if opts.public_key_path is not None and not opts.public_key_path.endswith(".pub"):
        print(">>> Please provide a PUBLIC key (.pub) to install on the remote machines")
        sys.exit(1)

    install_keys(
        opts.public_key_path,
        opts.ssh_user,
        opts.ssh_password,
    )
