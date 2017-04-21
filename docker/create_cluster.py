from __future__ import print_function

import argparse
import subprocess
import json
import os
import shutil

import docker

from keywords.exceptions import DockerError


def remove_networks(docker_client, network_name):
    """ Removes all user defined docker networks """

    networks = docker_client.networks.list()

    # Filter out docker defined networks
    user_defined_network = [network for network in networks if network.name == network_name]
    if len(user_defined_network) == 1:
        print('Removing network {}'.format(user_defined_network[0].name))
        user_defined_network[0].remove()

    # Verify that all user defined networks are removed
    networks = docker_client.networks.list()
    user_defined_network = [network for network in networks if network.name == network_name]
    if len(user_defined_network) != 0:
        raise DockerError('Failed to remove all networks!')


def remove_containers(docker_client, network_name):
    """ Stops / removes all containers """

    containers = docker_client.containers.list(all=True)
    for container in containers:

        # Only remove the container if it starts with the network prefix
        if container.name.startswith(network_name):
            print('Stopping / removing containers with prefix {}: {}'.format(network_name, container.name))
            subprocess.check_call(['docker', 'stop', container.name])
            subprocess.check_call(['docker', 'rm', container.name])

    # Verify that all containers have been removed
    containers = docker_client.containers.list(all=True)
    containers_to_verify_removed = [container for container in containers if container.name.startswith(network_name)]
    if len(containers_to_verify_removed) != 0:
        raise DockerError('Failed to remove all containers!')


def create_cluster(clean, network_name, number_of_nodes, public_key_path):

    docker_client = docker.from_env()

    print('Pulling sethrosetter/centos7-systemd-sshd image ...')
    docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

    print('Pulling couchbase/mobile-testkit image ...')
    docker_client.images.pull('couchbase/mobile-testkit')

    if clean:
        print('Cleaning environment')
        remove_containers(docker_client, network_name)
        remove_networks(docker_client, network_name)

    # Create docker network with name
    print('Creating bridged network: {} ...'.format(network_name))
    network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    print('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))
    container_names = ['{}.{}'.format(network_name, i) for i in range(number_of_nodes)]

    is_first = True
    for container_name in container_names:

        print('Starting container: {} on network: {}'.format(container_name, network_name))

        # Delete / Create tmp mount dir
        tmp_dir = '/tmp/{}'.format(container_name)

        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.mkdir(tmp_dir)

        # Priviledged is required for some ansible playbooks
        # The volume binding is needed for systemd
        # https://hub.docker.com/r/centos/systemd/
        if is_first:
            # Hack, Currently the first container will always be a Couchbase Server. We want to bind
            # it to localhost so that we can debug using the Admin UI
            container = docker_client.containers.run(
                'sethrosetter/centos7-systemd-sshd',
                detach=True,
                name=container_name,
                privileged=True,
                volumes={
                    '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'},
                    tmp_dir: {'bind': '/home'}
                },
                ports={'8091/tcp': 18091}
            )
            is_first = False
        else:
            container = docker_client.containers.run(
                'sethrosetter/centos7-systemd-sshd',
                detach=True,
                name=container_name,
                privileged=True,
                volumes={
                    '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'},
                    tmp_dir: {'bind': '/home'}
                }
            )
        network.connect(container)

        # Deploy public key to cluster containers
        # HACK: Using subprocess here since docker-py does not support copy
        # TODO: Use .tar with client.put_achive
        print('Deploying key: {} to {}:/root/.ssh/authorized_users'.format(public_key_path, container_name))
        subprocess.check_call([
            'docker',
            'cp',
            public_key_path,
            '{}:/root/.ssh/authorized_keys'.format(container_name)
        ])

    # Write cluster hosts to pool.json
    with open('/tmp/pool.json', 'w') as f:
        hosts = {'ips': container_names}
        f.write(json.dumps(hosts))


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
