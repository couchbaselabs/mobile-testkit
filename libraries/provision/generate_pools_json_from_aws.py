
import ec2
import ansible.inventory
from optparse import OptionParser
import sys
import json


# This generates a pool.json file from the current AWS EC2 inventory.
# The pool.json file can then be used to generate cluster configs under resources/cluster_configs

def write_to_file(cloud_formation_stack_dns_addresses, filename):
    """
    {
        "ips": [
	        "ec2-54-242-119-83.compute-1.amazonaws.com",
	        "ec2-54-242-119-84.compute-1.amazonaws.com",
        ]
    }
    """
    output_dictionary = {"ips": cloud_formation_stack_dns_addresses}

    with open(filename, 'w') as target:
        target.truncate()
        target.write(json.dumps(output_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))

def lookup_dns_names(inventory, cloud_formation_stack_ip_addresses):
    """
    Given

    [u'54.242.119.83', u'54.234.207.138'..]

    Return

    [u'ec2-54-242-119-83.compute-1.amazonaws.com', etc..]

    """

    return [inventory["_meta"]["hostvars"][ip_address]["ec2_public_dns_name"] for ip_address in cloud_formation_stack_ip_addresses]


if __name__=="__main__":

    usage = """usage: python generate_ansible_inventory_from_aws.py
    --stackname=<aws_cloudformation_stack_name>
    --targetfile=<ansible_inventory_target_file_path>
    --dumpinventory=true|false
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--stackname",
                      action="store", type="string", dest="stackname", default=None,
                      help="aws cloudformation stack name")

    parser.add_option("", "--targetfile",
                      action="store", type="string", dest="targetfile", default=None,
                      help="ansible inventory target file")

    parser.add_option("", "--dumpinventory",
                      action="store", dest="dumpinventory", default=False,
                      help="dump raw AWS inventory (for debugging)")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.stackname is None or opts.targetfile is None:
        print("You must specify --stackname=<stack_name> and --targetfile=<file_name>")
        sys.exit(1)

    print "Getting inventory from AWS ... (may take a few minutes)"
    ec2Inventory = ec2.Ec2Inventory()

    # print "Refreshing inventory from AWS ... (may take a few minutes)"
    ec2Inventory.do_api_calls_update_cache()

    # the inventory will contain all the hosts for the given cloudformation stack
    # under a key that looks like tag_aws_cloudformation_stack_name_TLeydenTestCluster
    cloud_formation_stack_key = "tag_aws_cloudformation_stack_name_{}".format(opts.stackname)

    # get all hosts for that cloudformation stack + uniquify
    if opts.dumpinventory:
        print "Inventory: {}".format(json.dumps(ec2Inventory.inventory, indent=4))


    # it's important that these are in the _same order_ as they are generated in generate_clusters_from_pool.py
    # so that things "line up" and the right machines are used for the role type as specified in the
    # initial call to create_and_instantiate_cluster.py.  It's a bit of a hack, and very brittle, and should
    # be reworked to explicitly record the machine size somewhere, or assert that the vm's spun up
    # all have the identical sizes.
    couchbase_server_ip_addresses = ec2Inventory.inventory["tag_Type_couchbaseserver"]
    print("couchbase_server_ip_addresses: {}".format(couchbase_server_ip_addresses))
    sync_gateway_ip_addresses = ec2Inventory.inventory["tag_Type_syncgateway"]
    print("sync_gateway_ip_addresses: {}".format(sync_gateway_ip_addresses))
    load_generator_ip_addresses = ec2Inventory.inventory["tag_Type_gateload"]
    print("load_generator_ip_addresses: {}".format(load_generator_ip_addresses))

    # get ip addresses of [u'54.242.119.83', u'54.234.207.138', u'54.209.218.97', u'54.242.55.56', u'54.242.29.78', u'52.90.171.161', u'54.175.81.204']
    cloud_formation_stack_ip_addresses = couchbase_server_ip_addresses + sync_gateway_ip_addresses + load_generator_ip_addresses
    print("cloud_formation_stack_ip_addresses: {}".format(cloud_formation_stack_ip_addresses))
    
    # convert to dns names
    cloud_formation_stack_dns_addresses = lookup_dns_names(ec2Inventory.inventory, cloud_formation_stack_ip_addresses)

    write_to_file(cloud_formation_stack_dns_addresses, opts.targetfile)

    print "Generated {}".format(opts.targetfile)

