import argparse
import json
import os
import shutil
import subprocess

import docker
from docker.errors import NotFound
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


def create_cluster(network_name, number_of_nodes, dev, pull):

    docker_client = docker.from_env()

    if pull:
        log_info('Pulling couchbase/centos7-systemd image ...')
        docker_client.images.pull('couchbase/centos7-systemd', tag='latest')

        log_info('Pulling couchbase/mobile-testkit image ...')
        docker_client.images.pull('couchbase/mobile-testkit', tag='latest')

    # Create docker network with name
    log_info('Checking if network ({}) exists ...'.format(network_name))

    conflicting_networks = [net for net in docker_client.networks.list() if net.name == network_name]

    # If there is a network defined with the name of one you are trying to create
    # Dev mode: reuse the existing network
    # Strict mode: raise an exception
    if len(conflicting_networks) > 0:
        if not dev:
            raise DockerError('ERROR!! Network already defined')
        log_info('Using already defined network: {}'.format(network_name))
        network = conflicting_networks[0]
    else:
        log_info('Creating bridged network: {} ...'.format(network_name))
        network = docker_client.networks.create(network_name)

    # Loop through nodes, start them on the network that was just created
    log_info('Starting {} containers on network {} ...'.format(number_of_nodes, network_name))
    container_names = ['{}.{}'.format(network_name, i) for i in range(number_of_nodes)]

    # TODO: discover the highest local port being used, and start from there, otherwise will give error:
    # 500 Server Error: Internal Server Error ("driver failed programming external connectivity on endpoint
    # tleyden1.0 (83c5dcdb0b12332dad5e69a904c330587d70f9a7e0d85dd69f6e724b3e287963): Bind for 0.0.0.0:30000
    # failed: port is already allocated")
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
            'couchbase/centos7-systemd',
            detach=True,
            name=container_name,
            privileged=True,
            volumes=volume_map,
            ports=port_map
        )

        # Connect running container to the network
        network.connect(container)

    # Write port map list if dev
    if dev:
        with open('portmaps.json', 'w') as port_map_file:
            port_map_file.write(json.dumps(port_map_list, indent=4))

    # Write cluster hosts to pool.json
    with open('resources/pool.json', 'w') as f:
        log_info("Writing 'resources/pool.json' ...")
        hosts = {'ips': container_names}
        f.write(json.dumps(hosts))


def destroy_cluster(network_name):
    """ Removes all user defined docker networks """

    docker_client = docker.from_env()

    # Get networks in docker host
    networks = docker_client.networks.list()

    # Filter network to match network name
    network_to_destroy = [network for network in networks if network.name == network_name]
    if len(network_to_destroy) > 1:
        raise DockerError('Error removing network. Multiple defined: {}'.format(network_name))
    if len(network_to_destroy) == 0:
        raise DockerError('Error removing network. Network not defined: {}'.format(network_name))
    network_to_destroy = network_to_destroy[0]

    # Get docker containers for the network
    network_containers = network_to_destroy.containers
    for network_container in network_containers:

        # Remove the containers attached to this network
        log_info('Removing container: {}'.format(network_container.name))
        subprocess.check_call(['docker', 'stop', network_container.name])
        subprocess.check_call(['docker', 'rm', '-f', network_container.name])

    # Verify that containers have been removed
    try:
        network_containers = network_to_destroy.containers
        # if the above call succeeds, it means there are still containers attached
        # to the network, raise an exception
        raise DockerError('During network cleanup, Docker containers still remain!')
    except NotFound:
        # A not found exception was raise so all the containers are gone. Proceed.
        log_info('All containers removed from the network!')

    # Remove the network
    log_info('Removing network {}'.format(network_to_destroy.name))
    network_to_destroy.remove()

    # Verify that all user defined networks are removed
    networks = docker_client.networks.list()
    user_defined_network = [network for network in networks if network.name == network_name]
    if len(user_defined_network) != 0:
        raise DockerError('Failed to remove all networks!')


if __name__ == '__main__':

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--create', help='Create a docker network + cluster', action='store_true')
    PARSER.add_argument('--destroy', help='Remove a docker network + cluster', action='store_true')
    PARSER.add_argument('--network-name', help='Name of docker network', required=True)
    PARSER.add_argument('--number-of-nodes', help='Number of nodes to create in the network')
    PARSER.add_argument('--dev', help='Using a dev environment, set up binding to log dirs and port binding for Couchbase Server', action='store_true')
    PARSER.add_argument('--pull', help='Specify whether to pull the latest docker containers', action='store_true')
    ARGS = PARSER.parse_args()

    if not ARGS.create and not ARGS.destroy:
        raise DockerError("You need to specify either '--create' or '--destroy'")

    if ARGS.create and ARGS.destroy:
        raise DockerError("You can't specify '--create' and '--destroy'. Please pick one.")

    # Scan all log files in the directory for 'panic' and 'data races'
    if ARGS.create:

        if ARGS.number_of_nodes is None:
            raise DockerError("You need to specify '--number-of-nodes'")

        create_cluster(
            network_name=ARGS.network_name,
            number_of_nodes=int(ARGS.number_of_nodes),
            dev=ARGS.dev,
            pull=ARGS.pull
        )
    else:
        destroy_cluster(
            network_name=ARGS.network_name
        )
