import argparse
import subprocess
import json


def teardown_tunnel(remote_hosts):
    for remote_host in remote_hosts:
        output = subprocess.check_output([
            "ps auxww | grep -i ssh | grep -i {} | awk '{print $2}' | xargs kill".format(remote_host)
        ], shell=True)
        print(output)


if __name__ == "__main__":

    # There is some complex argument parsing going on in order to be able to capture
    # certain arguments and process them, and pass through the rest of the arguments
    # down to sgload being invoked.
    #
    # The parse_known_args() call will essentially extract any arguments added via
    # parser.add_argument(), and the rest of the arguments will get read into
    # sgload_arg_list_main and then passed to sgload when invoked

    parser = argparse.ArgumentParser()
    parser.add_argument('--remote-hosts-file')
    args = parser.parse_args()

    # TODO: Validate args

    # Load hosts file as array
    with open(args.remote_hosts_file) as f:
        pools = json.load(f)
        remote_hosts = pools['ips']
        print('Tearing down ssh tunneling for {} ... '.format(remote_hosts))

    teardown_tunnel(remote_hosts)



