import argparse
import os
import tarfile

import docker
import dockerpty

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

    docker_client = docker.from_env()

    print('Pulling sethrosetter/centos7-systemd-sshd image ...')
    docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

    print('Pulling couchbase/mobile-testkit image ...')
    docker_client.images.pull('couchbase/mobile-testkit')

    if clean:
        print('Cleaning environment')
        remove_containers(docker_client)
        remove_networks(docker_client)

    # Create docker network with name
    print('Creating bridged network: {} ...'.format(network_name))
    network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    print('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))

    # Create tarfile of public key to upload to all the containers.
    # The tar file will be automatically extracted on the target after copy.
    # HACK: Our public key that we pass will automatically be untared as authorized_users in
    # the container
    tarfile_name = 'pub_key.tar'
    with tarfile.open(tarfile_name, 'w') as tar_file:
        tar_file.add(public_key_path, arcname='authorized_users')

    # Open tarfile as stream
    tarfile_stream = open(tarfile_name, "rb")

    container_names = ['{}_{}'.format(network_name, i) for i in range(number_of_nodes)]
    for container_name in container_names:

        print('Starting container: {} on network: {}'.format(container_name, network_name))

        container = docker_client.containers.run(
            'sethrosetter/centos7-systemd-sshd',
            detach=True,
            name=container_name,
            volumes={
                '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'}
            }
        )
        network.connect(container)

        # Deploy key to docker containers
        # HACK: Currently the docker python client only supports copying tar files from host to client
        print('Deploying key: {} to {}:/root/.ssh/authorized_users'.format(public_key_path, container_name))
        docker_client.api.put_archive(
            container=container.id,
            path='/root/.ssh',
            data=tarfile_stream
        )

    # Remove .tar.gz
    tarfile_stream.close()
    os.remove(tarfile_name)

    # Start testkit container
    container_name = 'mobile-testkit'
    print("Starting container: 'mobile-testkit' on network: {}".format(network_name))
    container = docker_client.containers.run(
        'couchbase/mobile-testkit',
        name=container_name,
        detach=True,
        tty=True
    )
    network.connect(container)

    import pdb
    pdb.set_trace()

    tarfile_name = 'priv_key.tar'
    private_key_path = public_key_path.replace('.pub', '')
    private_key_name = os.path.split(private_key_path)[-1]
    with tarfile.open(tarfile_name, 'w') as tar_file:
        tar_file.add(private_key_path, arcname=private_key_name)

    # Open tarfile as stream
    tarfile_stream = open(tarfile_name, "rb")

    print('Deploying private key: {} to {}:/root/.ssh/'.format(private_key_path, container_name))
    docker_client.api.put_archive(
        container=container.id,
        path='/root/.ssh',
        data=tarfile_stream
    )

    # Remove .tar.gz
    tarfile_stream.close()
    os.remove(tarfile_name)

    import pdb
    pdb.set_trace()

    # Drop into mobile-testkit shell
    # print("Starting /bin/bash for 'mobile-testkit'")
    # dockerpty.PseudoTerminal(docker_client, container).start()


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
