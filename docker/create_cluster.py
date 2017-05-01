from __future__ import print_function

import argparse
import subprocess
import json
import os
import shutil

import docker

from keywords.exceptions import DockerError


def remove_conflicting_network(docker_client, network_name):
    """ Removes all user defined docker networks """

    networks = docker_client.networks.list()

    # If a network exists with the name of the one you requested to create
    # remove the network and create a new one
    user_defined_networks = [network for network in networks if network.name == network_name]
    for user_defined_network in user_defined_networks:

        print('Removing containers for network ({})'.format(user_defined_network.name))

        # Get docker containers for the network
        network_containers = user_defined_network.containers
        for network_container in network_containers:

            # Remove the containers attached to this network
            print('Removing container: {}'.format(network_container.name))
            subprocess.check_call(['docker', 'stop', network_container.name])
            subprocess.check_call(['docker', 'rm', '-f', network_container.name])

        # Remove the network
        print('Removing network {}'.format(user_defined_network.name))
        user_defined_network.remove()

    # Verify that all user defined networks are removed
    networks = docker_client.networks.list()
    user_defined_network = [network for network in networks if network.name == network_name]
    if len(user_defined_network) != 0:
        raise DockerError('Failed to remove all networks!')


def create_cluster(pull, clean, network_name, number_of_nodes, public_key_path):

    docker_client = docker.from_env()

    if pull:
        print('Pulling sethrosetter/centos7-systemd-sshd image ...')
        docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

        print('Pulling couchbase/mobile-testkit image ...')
        docker_client.images.pull('couchbase/mobile-testkit')

    if clean:
        print('Cleaning environment')
        remove_conflicting_network(docker_client, network_name)

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

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--pull', help='Specify whether to pull the latest docker containers', action='store_true')
    PARSER.add_argument('--clean', help='Remove all user defined networks / container', action='store_true')
    PARSER.add_argument('--network-name', help='Name of docker network', required=True)
    PARSER.add_argument('--number-of-nodes', help='Number of nodes to create in the network', required=True)
    PARSER.add_argument('--path-to-public-key', help='Number of nodes to create in the network', required=True)
    ARGS = PARSER.parse_args()

    # Scan all log files in the directory for 'panic' and 'data races'
    create_cluster(
        pull=ARGS.pull,
        clean=ARGS.clean,
        network_name=ARGS.network_name,
        number_of_nodes=int(ARGS.number_of_nodes),
        public_key_path=ARGS.path_to_public_key
    )
