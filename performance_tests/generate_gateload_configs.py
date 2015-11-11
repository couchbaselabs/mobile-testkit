
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
import json
import os
from jinja2 import Template
import ansible.inventory

def sync_gateways():
    """
    Get the list of sync gateway private ip addresses
    """
    tag = "sync_gateways"
    public_ips = []
    instance_list = public_ip_addresses_for_tag(tag)
    print "sync gw instance_list: {}".format(instance_list)
    for public_ip in instance_list:
        if len(public_ip) == 0:
            continue
        print "sync gw public ip: {}".format(public_ip)
        public_ips.append(public_ip)

    return public_ips


def public_ip_addresses_for_tag(tag):
    hostfile = "../../../temp_ansible_hosts"
    i = ansible.inventory.Inventory(host_list=hostfile)
    hosts = i.get_group(tag).get_hosts()
    return [host.get_variables()['ansible_ssh_host'] for host in hosts]

def gateloads():
    tag = "load_generators"
    gateloads = []
    instance_list = public_ip_addresses_for_tag(tag)

    for public_ip in instance_list:
        if len(public_ip) == 0:
            continue
        print "gateload public ip: {}".format(public_ip)
        gateloads.append(public_ip)

    return gateloads

def render_gateload_template(sync_gateway_private_ip, user_offset, number_of_pullers, number_of_pushers):
        # run template to produce file
        gateload_config = open("files/gateload_config.json")
        template = Template(gateload_config.read())
        rendered = template.render(
            sync_gateway_private_ip=sync_gateway_private_ip,
            user_offset=user_offset,
            number_of_pullers=number_of_pullers,
            number_of_pushers=number_of_pushers
        )
        return rendered 

def upload_gateload_config(gateload_ec2_id, sync_gateway_private_ip, user_offset, number_of_pullers, number_of_pushers):
    
    rendered = render_gateload_template(
        sync_gateway_private_ip,
        user_offset,
        number_of_pullers,
        number_of_pushers
    )
    print rendered

    outfile = os.path.join("/tmp", gateload_ec2_id) 
    with open(outfile, 'w') as f:
        f.write(rendered)
    print "Wrote to file: {}".format(outfile)

    # transfer file to remote host
    cmd = 'ansible {} -i ../../../temp_ansible_hosts -m copy -a "src={} dest=/home/centos/gateload_config.json" --user centos'.format(gateload_ec2_id, outfile)
    result = subprocess.check_output(cmd, shell=True)
    print "File transfer result: {}".format(result)


def main(number_of_pullers, number_of_pushers):

    sync_gateway_ips = sync_gateways()

    gateload_ips = gateloads()

    for idx, gateload_ip in enumerate(gateload_ips):

        # calculate the user offset
        total_num_users = number_of_pullers + number_of_pushers
        user_offset = idx * total_num_users

        # assign a sync gateway to this gateload, get its ip
        sync_gateway_private_ip = sync_gateway_ips[idx]

        upload_gateload_config(
            gateload_ip,
            sync_gateway_private_ip,
            user_offset,
            number_of_pullers,
            number_of_pushers
        )

    print "Finished successfully"

if __name__ == "__main__":
    main(100, 100)

