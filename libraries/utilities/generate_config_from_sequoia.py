import argparse
import json
import shutil

from keywords.utils import log_info
from keywords.constants import CLUSTER_CONFIGS_DIR


def verify_services(host_json, num_servers, num_sync_gateways, num_accels):
    if len(host_json['couchbase_servers']) != num_servers:
        raise ValueError('Make sure you have the correct number of servers')
    if len(host_json['sync_gateways']) != num_sync_gateways:
        raise ValueError('Make sure you have the correct number of sync_gateways')
    if len(host_json['sg_accels']) != num_accels:
        raise ValueError('Make sure you have the correct number of sg_accels')


def verify_topology(topology, host_json):

    if topology == 'base_cc':
        verify_services(host_json, num_servers=1, num_sync_gateways=1, num_accels=0)
    elif topology == 'base_di':
        verify_services(host_json, num_servers=1, num_sync_gateways=1, num_accels=1)
    elif topology == 'ci_cc':
        verify_services(host_json, num_servers=3, num_sync_gateways=1, num_accels=0)
    elif topology == 'ci_di':
        verify_services(host_json, num_servers=3, num_sync_gateways=1, num_accels=3)
    else:
        raise ValueError('Make sure you topology is one of the above!')


def generate_config_from_sequoia(host_file, topology):

    cluster_config_file_name = '{}/{}'.format(CLUSTER_CONFIGS_DIR, topology)
    json_file_name = '{}.json'.format(cluster_config_file_name)

    with open(host_file) as f:
        host_json = json.loads(f.read())
    verify_topology(topology, host_json)

    # Copy / rename host file configuration to cluster_config directory
    shutil.copyfile(host_file, json_file_name)

    couchbase_servers = host_json['couchbase_servers']
    sync_gateways = host_json['sync_gateways']
    sg_accels = host_json['sg_accels']
    load_generators = host_json['load_generators']
    load_balancers = host_json['load_balancers']

    cluster_config_path = 'resources/cluster_configs/{}'.format(topology)
    log_info('Writing cluster config: {}'.format(cluster_config_path))

    with open(cluster_config_path, 'w') as f:

        f.write('[couchbase_servers]\n')
        for couchbase_server in couchbase_servers:
            f.write('{} ansible_host={} ansible_connection=docker\n'.format(couchbase_server['name'], couchbase_server['ip']))

        f.write('\n[sync_gateways]\n')
        for sync_gateway in sync_gateways:
            f.write('{} ansible_host={} ansible_connection=docker\n'.format(sync_gateway['name'], sync_gateway['ip']))

        f.write('\n[sg_accels]\n')
        for sg_accel in sg_accels:
            f.write('{} ansible_host={} ansible_connection=docker\n'.format(sg_accel['name'], sg_accel['ip']))

        f.write('\n[load_generators]\n')
        for load_generator in load_generators:
            f.write('{} ansible_host={} ansible_connection=docker\n'.format(load_generator['name'], load_generator['ip']))

        f.write('\n[load_balancers]\n')
        for load_balancer in load_balancers:
            f.write('{} ansible_host={} ansible_connection=docker\n'.format(load_balancer['name'], load_balancer['ip']))

        f.write('\n[webhook_ip]\n')
        # TODO

        f.write('\n[environment]\n')
        f.write('cbs_ssl_enabled={}\n'.format(host_json['environment']['cbs_ssl_enabled']))
        f.write('xattrs_enabled={}\n'.format(host_json['environment']['xattrs_enabled']))


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser(description='Cluster config generator form sequoia host file')
    PARSER.add_argument('--host-file', help='Path to host file generated from sequoia', required=True)
    PARSER.add_argument('--topology', help='Topology to target for tests. Ex. base_cc', required=True)

    ARGS = PARSER.parse_args()
    generate_config_from_sequoia(ARGS.host_file, ARGS.topology)
