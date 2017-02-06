
"""

This attempts to automate the the Gateload config creation

* Find a list of ip's of all the sync gateway machines
* Find the ip of the writer and remove from the list
* Find a list of ip's of all the gateload machines
* Assert that list_sync_gateways and list_gateloads are of the same length
* Assign each gateload a sync gateway
* Assign each gateload a user offset (iterate over gateloads and bump by 13K)
* For each gateload
  * Generate gateload config from a template
    * Use assigned Sync Gateway ip
    * Use assigned user offset
  * Upload gateload config to gateload machine


"""

import subprocess
import os
from jinja2 import Template

import ansible.inventory
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible import constants

from libraries.provision.ansible_runner import PLAYBOOKS_HOME


def hosts_for_tag(cluster_config, tag):
    print(os.getcwd())

    variable_manager = VariableManager()
    loader = DataLoader()
    i = ansible.inventory.Inventory(loader=loader, variable_manager=variable_manager, host_list=cluster_config)

    group = i.get_group(tag)
    if group is None:
        return []
    hosts = group.get_hosts()
    return [host.get_vars() for host in hosts]


def gateloads(cluster_config):
    tag = "load_generators"
    return hosts_for_tag(cluster_config, tag)


def render_gateload_template(sync_gateway,
                             user_offset,
                             gateload_params):

        # run template to produce file
        gateload_config = open("{}/files/gateload_config.json".format(PLAYBOOKS_HOME))
        template = Template(gateload_config.read())
        rendered = template.render(
            sync_gateway_private_ip=sync_gateway['ansible_host'],
            user_offset=user_offset,
            number_of_pullers=gateload_params.number_pullers,
            number_of_pushers=gateload_params.number_pushers,
            doc_size=gateload_params.doc_size,
            runtime_ms=gateload_params.runtime_ms,
            rampup_interval_ms=gateload_params.rampup_interval_ms,
            feed_type=gateload_params.feed_type,
            sleep_time_ms=gateload_params.sleep_time_ms,
            channel_active_users=gateload_params.channel_active_users,
            channel_concurrent_users=gateload_params.channel_concurrent_users
        )
        return rendered


def upload_gateload_config(cluster_config,
                           gateload,
                           sync_gateway,
                           user_offset,
                           test_id,
                           gateload_params):

    gateload_inventory_hostname = gateload['inventory_hostname']

    rendered = render_gateload_template(
        sync_gateway=sync_gateway,
        user_offset=user_offset,
        gateload_params=gateload_params
    )
    print(rendered)

    # Write renderered gateload configs to test results directory
    with open("testsuites/syncgateway/performance/results/{}/{}.json".format(test_id, gateload_inventory_hostname), "w") as f:
        f.write(rendered)

    outfile = os.path.join("/tmp", gateload_inventory_hostname)
    with open(outfile, 'w') as f:
        f.write(rendered)
    print("Wrote to file: {}".format(outfile))

    # transfer file to remote host
    cmd = 'ansible {} -i {} -m copy -a "src={} dest=/home/centos/gateload_config.json" --user {}'.format(
        gateload_inventory_hostname,
        cluster_config,
        outfile,
        constants.DEFAULT_REMOTE_USER
    )
    print("Uploading gateload config using command: {}".format(cmd))
    result = subprocess.check_output(cmd, shell=True)
    print("File transfer result: {}".format(result))


def main(cluster_config, test_id, gateload_params):

    sync_gateway_hosts = hosts_for_tag(cluster_config, "sync_gateways")

    gateload_hosts = gateloads(cluster_config)

    if len(sync_gateway_hosts) != len(gateload_hosts):
        print("Warning: you have {} sync gateway non index writers, but does not match up with {} load generators".format(len(sync_gateway_hosts), len(gateload_hosts)))

    for idx, gateload in enumerate(gateload_hosts):

        # calculate the user offset
        total_num_users = int(gateload_params.number_pullers) + int(gateload_params.number_pushers)
        user_offset = idx * total_num_users

        # assign a sync gateway to this gateload, get its ip
        sync_gateway = sync_gateway_hosts[idx]

        upload_gateload_config(
            cluster_config=cluster_config,
            gateload=gateload,
            sync_gateway=sync_gateway,
            user_offset=user_offset,
            test_id=test_id,
            gateload_params=gateload_params
        )

    print("Finished successfully")
