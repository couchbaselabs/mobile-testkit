
from optparse import OptionParser
import sys
import json
import time
from boto import cloudformation
from boto import ec2

# This generates a pool.json file from the current AWS EC2 inventory.
# The pool.json file can then be used to generate cluster configs under resources/cluster_configs

DEFAULT_REGION="us-east-1"

def main():

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
                      action="store", type="string", dest="targetfile", default="resources/pool.json",
                      help="ansible inventory target file")

    parser.add_option("", "--dumpinventory",
                      action="store", dest="dumpinventory", default=False,
                      help="dump raw AWS inventory (for debugging)")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.stackname is None or opts.targetfile is None:
        print("You must specify --stackname=<stack_name>")
        sys.exit(1)

    pool_dns_addresses = generate_pools(opts.stackname, opts.dumpinventory)

    print("pool_dns_addresses: {}".format(pool_dns_addresses))

    write_to_file(pool_dns_addresses, opts.targetfile)

    print "Generated {}".format(opts.targetfile)

def generate_pools(stackname, dumpinventory):

    # wait for stack creation to finish
    wait_until_stack_create_complete(stackname)

    # find all ec2 instance ids for stack
    instance_ids_for_stack = get_instance_ids_for_stack(stackname)

    # get list of instance objects from ids
    instances_for_stack = lookup_instances_from_ids(instance_ids_for_stack)

    # wait until stack ec2 instances are all in running state
    wait_until_state(instances_for_stack, instance_ids_for_stack, "running")

    # get public_dns_name for all instances
    return get_public_dns_names(instances_for_stack)

def get_instance_ids_for_stack(stackname):
    """
    For a given cloudformation stack, return all of the instance ids, eg
    ["i-f1430877", "i-g3430877", ...]
    """
    instance_ids_for_stack = []
    region = cloudformation.connect_to_region(DEFAULT_REGION)
    stack_resources = region.describe_stack_resources(stackname)
    for stack_resource in stack_resources:
        if stack_resource.resource_type == "AWS::EC2::Instance":
            instance_ids_for_stack.append(stack_resource.physical_resource_id)
    return instance_ids_for_stack

def lookup_instances_from_ids(instance_ids):
    """
    Given an array of instance ids, lookup the instance objects
    which will have all the metadata
    """
    instances = []
    region = ec2.connect_to_region(DEFAULT_REGION)
    reservations = region.get_all_instances(instance_ids)
    for reservation in reservations:
        for instance in reservation.instances:
            instances.append(instance)
    return instances

def wait_until_stack_create_complete(stackname):

    """
    Wait until this stack is complete.  In other words, when there is a stack event
    with:

    event.resource_type = AWS::CloudFormation::Stack
    event.resource_status = CREATE_COMPLETE
    """
    for x in xrange(10):
        print("Waiting for {} to finish launching.  Attempt: {}".format(stackname, x))
        region = cloudformation.connect_to_region(DEFAULT_REGION)
        stack_events = region.describe_stack_events(stackname)

        for stack_event in stack_events:
            if stack_event.logical_resource_id != stackname:
                print("Ignoring {} since it's not part of {}".format(stack_event, stackname))
                continue
            if stack_event.resource_type == "AWS::CloudFormation::Stack" and stack_event.resource_status == "CREATE_COMPLETE":
                print("Stack {} has successfully been created".format(stackname))
                return

        # didn't find it, lets wait and try again
        time.sleep(5)


def wait_until_state(instances, instance_ids, state):

    """
    Wait until all instances are in the given state.  The instance_ids are
    passed in case the instance objects need to be refreshed from AWS
    """
    print("Waiting for instances {} to be {}".format(instance_ids, state))
    for x in xrange(10):

        all_instances_in_state = True
        for instance in instances:
            if instance.state != state:
                all_instances_in_state = False

        # if all instances were in the given state, we're done
        if all_instances_in_state:
            return

        # otherwise ..
        print("Not all instances in {} were in state {}.  Waiting and will retry.. Iteration: {}".format(instance_ids, state, x))
        time.sleep(5)
        instances = lookup_instances_from_ids(instance_ids)

    raise Exception("Gave up waiting for instances {} to reach state {}".format(instance_ids, state))

def get_public_dns_names(instances):

    return [instance.public_dns_name for instance in instances]

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

if __name__=="__main__":

    main()
