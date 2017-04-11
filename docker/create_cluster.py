import argparse
import docker

from keywords.exceptions import DockerError


def remove_networks(docker_client):
    """ Removes all user defined docker networks """

    networks = docker_client.networks.list()

    # Filter out docker defined networks
    predefined_networks = ['bridge', 'none', 'host']
    user_defined_networks = [network for network in networks if network.name not in predefined_networks]

    for user_defined_network in user_defined_networks:
        print('Removing network: {}'.format(user_defined_network.name))
        user_defined_network.remove()

    # Verify that all user defined networks are removed
    networks = docker_client.networks.list()
    user_defined_networks = [network for network in networks if network.name not in predefined_networks]

    if len(user_defined_networks) != 0:
        raise DockerError('Failed to remove all networks!')


def remove_containers(docker_client):
    """ Stops / removes all containers """

    containers = docker_client.containers.list(all=True)
    for container in containers:
        print('Stopping / removing container: {}'.format(container.name))
        container.stop()
        container.remove()

    # Verify that all containers have been removed
    containers = docker_client.containers.list(all=True)
    if len(containers) != 0:
        raise DockerError('Failed to remove all containers!')


def create_cluster(clean, network_name, number_of_nodes, public_key_path):

    print('Pulling sethrosetter/centos7-systemd-sshd image ...')
    docker_client = docker.from_env()
    docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

    if clean:
        print('Cleaning environment')
        remove_containers(docker_client)
        remove_networks(docker_client)

    # Create docker network with name
    print('Creating bridged network: {} ...'.format(network_name))
    network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    print('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))
    for i in range(number_of_nodes):

        container_name = '{}_{}'.format(network_name, i)
        print('Starting container: {} on network: {}'.format(container_name, network_name))

        container = docker_client.containers.run(
            'sethrosetter/centos7-systemd-sshd',
            detach=True,
            name=container_name,
            networks=[network_name],
            volumes={
                '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'}
            }
        )
        network.connect(container)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--clean', help='Remove all user defined networks / container', action='store_true')
    parser.add_argument('--network-name', help='Name of docker network', required=True)
    parser.add_argument('--number-of-nodes', help='Number of nodes to create in the network', required=True)
    parser.add_argument('--path-to-public-key', help='Number of nodes to create in the network', required=True)
    args = parser.parse_args()

    # Scan all log files in the directory for 'panic' and 'data races'
    create_cluster(
        clean=args.clean,
        network_name=args.network_name,
        number_of_nodes=int(args.number_of_nodes),
        public_key_path=args.path_to_public_key
    )
