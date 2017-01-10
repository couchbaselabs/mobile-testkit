import argparse
import subprocess
import json


def setup_tunnel(target_host, target_port, remote_hosts_user, remote_hosts, remote_host_port):
    for remote_host in remote_hosts:
        proc = subprocess.Popen([
            'ssh',
            '{}@{}'.format(remote_hosts_user, remote_host),
            '-R',
            '{}:{}:{}'.format(remote_host_port, target_host, target_port),
            '-N',
            '-f'
        ])
        print("Running ssh tunnel with process id: {}".format(proc.pid))


if __name__ == "__main__":

    # There is some complex argument parsing going on in order to be able to capture
    # certain arguments and process them, and pass through the rest of the arguments
    # down to sgload being invoked.
    #
    # The parse_known_args() call will essentially extract any arguments added via
    # parser.add_argument(), and the rest of the arguments will get read into
    # sgload_arg_list_main and then passed to sgload when invoked

    parser = argparse.ArgumentParser()
    parser.add_argument('--target-host')
    parser.add_argument('--target-port')
    parser.add_argument('--remote-hosts-user')
    parser.add_argument('--remote-hosts-file')
    parser.add_argument('--remote-host-port')
    args = parser.parse_args()

    # TODO: Validate args

    # Load hosts file as array
    with open(args.remote_hosts_file) as f:
        pools = json.load(f)
        remote_hosts_list = pools['ips']
        print('Setting up ssh tunneling for {} ... '.format(remote_hosts_list))

    setup_tunnel(
        target_host=args.target_host,
        target_port=args.target_port,
        remote_hosts_user=args.remote_hosts_user,
        remote_hosts=remote_hosts_list,
        remote_host_port=args.remote_host_port
    )



