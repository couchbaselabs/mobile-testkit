import argparse
import docker


def remove_networks(list_of_networks):
    pass


def remove_containers(list_of_containers):
    pass


def create_cluster(network_name, number_of_nodes, public_key_path):

    print('Pulling sethrosetter/centos7-systemd-sshd image ...')
    docker_client = docker.from_env()
    docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

    networks = docker_client.networks.list()
    containers = docker_client.containers.list()

    remove_networks(networks)
    remove_containers(containers)

    # Create docker network with name
    print('Creating bridged network: {} ...'.format(network_name))
    network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    print('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))
    for i in range(number_of_nodes):
        container = docker_client.containers.run(
            'sethrosetter/centos7-systemd-sshd',
            detach=True,
            name='{}_{}'.format(network_name, i),
            networks=[network_name],
            volumes={
                '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'}
            }
        )
        network.connect(container)

    import pdb
    pdb.set_trace()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--network-name', help='Name of docker network', required=True)
    parser.add_argument('--number-of-nodes', help='Number of nodes to create in the network', required=True)
    parser.add_argument('--path-to-public-key', help='Number of nodes to create in the network', required=True)
    args = parser.parse_args()

    # Scan all log files in the directory for 'panic' and 'data races'
    create_cluster(
        network_name=args.network_name,
        number_of_nodes=int(args.number_of_nodes),
        public_key_path=args.path_to_public_key
    )
