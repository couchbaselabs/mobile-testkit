import argparse
import json
import os
import shutil
import subprocess

import docker
from keywords.exceptions import DockerError
from keywords.utils import log_info


def setup_port_mapping(current_port):
    """ Expose ports to host for local development """

    port_map = {}
    ports_to_map = ['8091/tcp', '4984/tcp', '4985/tcp']
    for port in ports_to_map:
        log_info('Setting up port binding: {} -> localhost:{}'.format(port, current_port))
        port_map[port] = current_port
        current_port += 1

    return port_map, current_port


def create_and_bind_tmp_dirs(container_name, volume_map):
    """ Create directories for binding the log directories for the various services.
    This provides quicker inspection / collection of the logs during devlopment """

    tmp_dir_sg = '/tmp/{}-sg'.format(container_name)
    tmp_dir_cbs = '/tmp/{}-cbs'.format(container_name)

    for tmp_dir in [tmp_dir_sg, tmp_dir_cbs]:
        log_info('Creating: {}'.format(tmp_dir))
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.mkdir(tmp_dir)

    volume_map[tmp_dir_sg] = {'bind': '/home'}
    volume_map[tmp_dir_cbs] = {'bind': '/opt/couchbase/var/lib/couchbase/'}

    return volume_map


# def remove_conflicting_network(docker_client, network_name):
#     """ Removes all user defined docker networks """

#     networks = docker_client.networks.list()

#     # If a network exists with the name of the one you requested to create
#     # remove the network and create a new one
#     user_defined_networks = [network for network in networks if network.name == network_name]
#     for user_defined_network in user_defined_networks:

#         log_info('Removing containers for network ({})'.format(user_defined_network.name))

#         # Get docker containers for the network
#         network_containers = user_defined_network.containers
#         for network_container in network_containers:

#             # Remove the containers attached to this network
#             log_info('Removing container: {}'.format(network_container.name))
#             subprocess.check_call(['docker', 'stop', network_container.name])
#             subprocess.check_call(['docker', 'rm', '-f', network_container.name])

#         # Remove the network
#         log_info('Removing network {}'.format(user_defined_network.name))
#         user_defined_network.remove()

#     # Verify that all user defined networks are removed
#     networks = docker_client.networks.list()
#     user_defined_network = [network for network in networks if network.name == network_name]
#     if len(user_defined_network) != 0:
#         raise DockerError('Failed to remove all networks!')


def create_cluster(network_name, number_of_nodes, public_key_path, dev, pull):

    docker_client = docker.from_env()

    if pull:
        log_info('Pulling sethrosetter/centos7-systemd-sshd image ...')
        docker_client.images.pull('sethrosetter/centos7-systemd-sshd')

        log_info('Pulling couchbase/mobile-testkit image ...')
        docker_client.images.pull('couchbase/mobile-testkit')

    # Create docker network with name
    log_info('Creating bridged network: {} ...'.format(network_name))
    network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    log_info('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))
    container_names = ['{}.{}'.format(network_name, i) for i in range(number_of_nodes)]

    current_port = 30000
    port_map_list = []
    for container_name in container_names:

        log_info('Starting container: {} on network: {}'.format(container_name, network_name))

        # The volume binding is needed for systemd
        # https://hub.docker.com/r/centos/systemd/
        volume_map = {
            '/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'}
        }
        port_map = {}
        if dev:
            # Setup local development enhancements
            volume_map = create_and_bind_tmp_dirs(container_name, volume_map)
            port_map, current_port = setup_port_mapping(current_port)
            port_map_list.append({container_name: port_map})

        # Priviledged is required for some ansible playbooks
        container = docker_client.containers.run(
            'sethrosetter/centos7-systemd-sshd',
            detach=True,
            name=container_name,
            privileged=True,
            volumes=volume_map,
            ports=port_map
        )

        # Connect running container to the network
        network.connect(container)

        # Deploy public key to cluster containers
        # HACK: Using subprocess here since docker-py does not support copy
        log_info('Deploying key: {} to {}:/root/.ssh/authorized_users'.format(public_key_path, container_name))
        subprocess.check_call([
            'docker',
            'cp',
            public_key_path,
            '{}:/root/.ssh/authorized_keys'.format(container_name)
        ])

    # Write port map list if dev
    if dev:
        with open('portmaps.json', 'w') as port_map_file:
            port_map_file.write(json.dumps(port_map_list, indent=4))

    # Write cluster hosts to pool.json
    with open('/tmp/pool.json', 'w') as f:
        hosts = {'ips': container_names}
        f.write(json.dumps(hosts))


if __name__ == '__main__':

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--network-name', help='Name of docker network', required=True)
    PARSER.add_argument('--number-of-nodes', help='Number of nodes to create in the network', required=True)
    PARSER.add_argument('--path-to-public-key', help='Number of nodes to create in the network', required=True)
    PARSER.add_argument('--dev', help='Using a dev environment, set up binding to log dirs and port binding for Couchbase Server', action='store_true')
    PARSER.add_argument('--pull', help='Specify whether to pull the latest docker containers', action='store_true')
    ARGS = PARSER.parse_args()

    # Scan all log files in the directory for 'panic' and 'data races'
    create_cluster(
        network_name=ARGS.network_name,
        number_of_nodes=int(ARGS.number_of_nodes),
        public_key_path=ARGS.path_to_public_key,
        dev=ARGS.dev,
        pull=ARGS.pull
    )
