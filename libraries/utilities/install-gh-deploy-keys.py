# This is required in order to build Sync Gateway + Sync Gateway Accel
# since Sync Gateway Accel is in a private repo.
#
# Keypair location: http://cbmobile-sharedkeys.s3.amazonaws.com/cbmobile_private_repo_read_only
#
# The public half of this key has already been added to the Settings of the Sync-Gateway-Accel
# github repo.  So anyone with the private key will be able to clone the repo.  The key is marked
# as read-only in github, so this key cannot be used to 'git push' to github.
#
# Instructions:
#
#  - Download the keypair from S3 to somewhere on your file system
#  - Run this script and point it at the keypair
#

import os
import subprocess
import sys

from optparse import OptionParser

from generate_clusters_from_pool import get_ips


def install_gh_deploy_keys(key_path, user_name):

    ips = get_ips()

    for ip in ips:

        if not os.path.exists(key_path):
            raise Exception("Cannot find key: {}".format(key_path))

        # Copy the key over to the /tmp directory.  Cannot copy directly to destination
        # (/root/.ssh/id_rsa) since it's not possible to use scp in conjunction w/ sudo.
        # Example: scp ~/tmp/cbmobile_private_repo_read_only vagrant@$TARGET:/tmp
        subprocess.check_output([
            "scp",
            "{}".format(key_path),
            "{}@{}:/tmp".format(user_name, ip)
        ])

        # Create the /root/.ssh directory if it doesn't already exist
        # The -tt flag is needed to avoid "sudo sorry, you must have a tty to run sudo" errors
        # See http://stackoverflow.com/questions/7114990/pseudo-terminal-will-not-be-allocated-because-stdin-is-not-a-terminal
        # Example: ssh vagrant@$TARGET "sudo mkdir /root/.ssh"
        subprocess.check_output([
            "ssh", "-tt", "{}@{}".format(
                user_name,
                ip,
            ), "sudo mkdir -p /root/.ssh"
        ])

        # Copy from the /tmp directory to the destination (/root/.ssh/id_rsa)
        # Example: ssh vagrant@$TARGET "sudo cp /tmp/cbmobile_private_repo_read_only /root/.ssh/id_rsa"
        key_filename = os.path.basename(key_path)
        subprocess.check_output([
            "ssh", "-tt", "{}@{}".format(
                user_name,
                ip,
            ), "sudo cp /tmp/{} /root/.ssh/id_rsa".format(
                key_filename,
            )
        ])

        # Chmod the id_rsa key to avoid the permissions are too open error
        # Example: ssh vagrant@$TARGET "sudo chmod /root/.ssh/id_rsa"
        subprocess.check_output([
            "ssh", "-tt", "{}@{}".format(
                user_name,
                ip,
            ), "sudo chmod 400 /root/.ssh/id_rsa"
        ])

        # Add the github.com public key to /root/.ssh/known_hosts
        # Example: ssh vagrant@$TARGET "sudo ssh-keyscan -t rsa github.com | sudo tee /root/.ssh/known_hosts"
        subprocess.check_output([
            "ssh", "-tt", "{}@{}".format(
                user_name,
                ip,
            ), "sudo ssh-keyscan -t rsa github.com | sudo tee /root/.ssh/known_hosts"
        ])


if __name__ == "__main__":

    usage = "usage: install-gh-deploy-keys.py --key-path=<path_to_private_deploy_key> --ssh-user=<user>"
    parser = OptionParser(usage=usage)

    parser.add_option(
        "", "--key-path",
        action="store",
        type="string",
        dest="key_path",
        help="private ssh deploy <key to install to hosts",
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
        print(">>> Please provide --key-path=<path_to_private_deploy_key> AND --ssh-user=<user>")
        sys.exit(1)

    install_gh_deploy_keys(opts.key_path, opts.ssh_user)

    print "Successful!"
