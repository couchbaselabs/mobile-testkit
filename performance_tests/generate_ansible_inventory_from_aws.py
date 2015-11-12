
import ec2
import ansible.inventory
from optparse import OptionParser
import sys

"""
Generate a temp_ansible_hosts file like:

[couchbase_servers]
cb1 ansible_ssh_host=ec2-54-147-234-108.compute-1.amazonaws.com

[sync_gateways]
sg1 ansible_ssh_host=ec2-50-16-26-70.compute-1.amazonaws.com

[load_generators]
lg1 ansible_ssh_host=ec2-54-157-59-199.compute-1.amazonaws.com

"""

host_types = [
    "tag_Type_syncgateway", 
    "tag_Type_couchbaseserver", 
    "tag_Type_gateload",
    "tag_Type_loadbalancer"
]
host_types_to_ansible_groups = {
    "tag_Type_syncgateway": "sync_gateways",
    "tag_Type_couchbaseserver": "couchbase_servers",
    "tag_Type_gateload": "load_generators",
    "tag_Type_loadbalancer": "load_balancers"
}
ansible_group_shortnames = {
    "sync_gateways": "sg",
    "couchbase_servers": "cb",
    "load_generators": "lg",
    "load_balancer": "lb"
}

def get_ansible_inventory_name(ansible_group_name, host_index):
    """
    Given ansible group name of "sync_gateways" and host_index of 2, 
    return sg2
    """
    ansible_group_shortname = ansible_group_shortnames[ansible_group_name]
    return "{}{}".format(ansible_group_shortname, host_index)

def get_ansible_groups():

    ansible_groups = []

    # loop over all the host_types (groups) like 
    for host_type in host_types:
        
        if not ec2Inventory.inventory.has_key(host_type):
            print "No hosts with type: {} found, skipping".format(host_type)
            continue

        hosts_for_type = ec2Inventory.inventory[host_type]
        hosts_for_type = list(set(hosts_for_type))  # uniquify

        # find the intersection of hosts for this host type which are in cloudformation stack
        hostnames = [host for host in hosts_for_type if host in cloud_formation_stack_hostnames]

        # convert from ec2 tag -> ansible group: eg, tag_Type_syncgateway -> sync_gateways
        ansible_group_name = host_types_to_ansible_groups[host_type]

        # create an ansible group object
        ansible_group = ansible.inventory.group.Group(ansible_group_name)

        i = 1
        for hostname in hostnames:

            # the inventory name, eg "sg1"
            ansible_inventory_name = get_ansible_inventory_name(ansible_group_name, i)

            # create an ansible host object
            host = ansible.inventory.host.Host(ansible_inventory_name)
            host.add_group(ansible_group)
            host.set_variable("ansible_ssh_host", hostname)
            ansible_group.add_host(host)
            i += 1

        ansible_groups.append(ansible_group)

    return ansible_groups

def write_to_file(ansible_groups, filename):
    target = open(filename, 'w')
    target.truncate()
    for ansible_group in ansible_groups:
        group_header = "[{}]".format(ansible_group.name)
        target.write(group_header)
        target.write("\n")
        for ansible_host in ansible_group.get_hosts():
            host_variables = ansible_host.get_variables()
            target.write(ansible_host.name)
            target.write(" ")
            ansible_ssh_host = host_variables["ansible_ssh_host"]
            line = "ansible_ssh_host={}".format(ansible_ssh_host)
            target.write(line)
            target.write("\n")

        target.write("\n")

    target.close()
    print "Ansible inventory written to: {}".format(filename)

if __name__=="__main__":

    usage = """usage: python generate_ansible_inventory_from_aws.py
    --stackname=<aws_cloudformation_stack_name>
    --targetfile=<ansible_inventory_target_file_path>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--stackname",
                      action="store", type="string", dest="stackname", default=None,
                      help="aws cloudformation stack name")

    parser.add_option("", "--targetfile",
                      action="store", type="string", dest="targetfile", default=None,
                      help="ansible inventory target file")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    print "Getting inventory from AWS ... (may take a few minutes)"
    ec2Inventory = ec2.Ec2Inventory()
    # print "Refreshing inventory from AWS ... (may take a few minutes)"
    ec2Inventory.do_api_calls_update_cache()

    # the inventory will contain all the hosts for the given cloudformation stack
    # under a key that looks like tag_aws_cloudformation_stack_name_TLeydenTestCluster
    cloud_formation_stack_key = "tag_aws_cloudformation_stack_name_{}".format(opts.stackname)

    # get all hosts for that cloudformation stack + uniquify
    cloud_formation_stack_hostnames = ec2Inventory.inventory[cloud_formation_stack_key]
    cloud_formation_stack_hostnames = list(set(cloud_formation_stack_hostnames))

    ansible_groups = get_ansible_groups()
    write_to_file(ansible_groups, opts.targetfile)

        

