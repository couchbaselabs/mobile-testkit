
from optparse import OptionParser
import sys
import json
import time
from boto import cloudformation
from boto import ec2
from boto.exception import BotoServerError

import socket

# This generates a pool.json file from the current AWS EC2 inventory.
# The pool.json file can then be used to generate cluster configs under resources/cluster_configs

DEFAULT_REGION = "us-east-1"
NUM_RETRIES = 50


def main():

    usage = """usage: python generate_pools_json_from_aws.py
        --stackname=<aws_cloudformation_stack_name>
        --targetfile=<ansible_inventory_target_file_path>
        """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--stackname",
                      action="store", type="string", dest="stackname", default=None,
                      help="aws cloudformation stack name")

    parser.add_option("", "--targetfile",
                      action="store", type="string", dest="targetfile", default="resources/pool.json",
                      help="ansible inventory target file")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.stackname is None or opts.targetfile is None:
        print("You must specify --stackname=<stack_name>")
        sys.exit(1)

    pool_dns_addresses = get_public_dns_names_cloudformation_stack(opts.stackname)

    print("pool_dns_addresses: {}".format(pool_dns_addresses))

    write_to_file(pool_dns_addresses, opts.targetfile)

    print "Generated {}".format(opts.targetfile)


def get_public_dns_names_cloudformation_stack(stackname):

    """
    Blocks until CloudFormation stack is fully up and running and all EC2 instances
    are listening on port 22.

    Returns the public DNS names of all EC2 instances in the stack
    """

    # wait for stack creation to finish
    wait_until_stack_create_complete(stackname)

    # find all ec2 instance ids for stack
    instance_ids_for_stack = get_instance_ids_for_stack(stackname)

    # get list of instance objects from ids
    instances_for_stack = lookup_instances_from_ids(instance_ids_for_stack)

    # wait until stack ec2 instances are all in running state
    wait_until_state(instances_for_stack, instance_ids_for_stack, "running")

    # wait until all ec2 instances are listening on port 22
    wait_until_sshd_port_listening(instances_for_stack)

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
    for x in xrange(NUM_RETRIES):
        print("Waiting for {} to finish launching.  Attempt: {}".format(stackname, x))
        region = cloudformation.connect_to_region(DEFAULT_REGION)

        try:
            region.describe_stacks(stackname)
        except BotoServerError as bse:
            print("Exception describing stack: {}, exception: {}. Retrying.".format(stackname, bse))
            continue

        stack_events = region.describe_stack_events(stackname)

        for stack_event in stack_events:
            if stack_event.stack_name != stackname:
                print("Ignoring {} since it's stack name is {} instead of {}".format(stack_event, stack_event.stack_name, stackname))
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

    for x in xrange(NUM_RETRIES):

        print("Waiting for instances {} to be {}".format(instance_ids, state))
        instances_not_in_state = []
        all_instances_in_state = True
        for instance in instances:
            if instance.state != state:
                instances_not_in_state.append(instance)
                all_instances_in_state = False

        # if all instances were in the given state, we're done
        if all_instances_in_state:
            return

        # otherwise ..
        print("The following instances are not yet in state {}: {}.  Waiting will retry.. Iteration: {}".format(instances_not_in_state, state, x))
        time.sleep(5)
        instances = lookup_instances_from_ids(instance_ids)

    raise Exception("Gave up waiting for instances {} to reach state {}".format(instance_ids, state))


def wait_until_sshd_port_listening(instances):

    for x in xrange(NUM_RETRIES):

        print("Waiting for instances to be listening on port 22")
        all_instances_listening = True
        for instance in instances:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client_socket.connect((instance.ip_address, 22))
            except Exception:
                print("Couldn't connect to {} on port 22".format(instance.ip_address))
                all_instances_listening = False

        # if all instances were in the given state, we're done
        if all_instances_listening:
            return

        # otherwise ..
        print("Not all instances listening on port 22.  Waiting and will retry.. Iteration: {}".format(x))
        time.sleep(5)

    raise Exception("Gave up waiting for instances to be listening on port 22")


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
        target.write(json.dumps(output_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))

if __name__ == "__main__":

    main()
