import json
import os
import subprocess
from optparse import OptionParser
from generate_cluster_configs_from_vagrant_hosts import check_network_options
import sys


def fix_password_auth(pool_file, private_network, public_network, public_network_ethernet):
    check_network_options(private_network, public_network, public_network_ethernet)

    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]

    cwd = os.getcwd()

    # Change directory to where the appropriate Vagrantfile lives
    if private_network:
        os.chdir("vagrant/private_network")
    elif public_network:
        os.chdir("vagrant/public_network")
    else:
        os.chdir("vagrant/public_network_ethernet")

    for i in range(len(ips)):
        host = "host" + str(i + 1)
        cmd = "vagrant ssh -c \"sudo sed -i -re 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \" " + host
        output = subprocess.check_output(cmd, shell=True)

        cmd = "vagrant ssh -c \"sudo grep -i PasswordAuthentication /etc/ssh/sshd_config \" " + host
        output = subprocess.check_output(cmd, shell=True)

        if "PasswordAuthentication yes" not in output:
            raise Exception("Failed to change the PasswordAuthentication flag for {}".format(host))

        cmd = "vagrant ssh -c \"sudo service sshd restart\" " + host
        output = subprocess.check_output(cmd, shell=True)

        if "Redirecting to /bin/systemctl restart  sshd.service" not in output:
            raise Exception("Failed to restart sshd for {}".format(host))

    os.chdir(cwd)


if __name__ == "__main__":
    usage = """
    usage: python ./utilities/fix_password_auth.py --private-network

       or

    usage: python ./utilities/fix_password_auth.py --public-network

       or

    usage: python ./utilities/fix_password_auth.py --public-network-ethernet
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--pool-file",
                      action="store", type="string", dest="pool_file", default="resources/pool.json",
                      help="path to pool.json file")

    parser.add_option("", "--private-network",
                      action="store_true", dest="private_network", default=False,
                      help="Use Vagrant private network (NAT)")

    parser.add_option("", "--public-network",
                      action="store_true", dest="public_network", default=False,
                      help="Use Vagrant public network (Bridged)")

    parser.add_option("", "--public-network-ethernet",
                      action="store_true", dest="public_network_ethernet", default=False,
                      help="Use Vagrant public ethernet network (Bridged)")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    fix_password_auth(opts.pool_file, opts.private_network, opts.public_network, opts.public_network_ethernet)
