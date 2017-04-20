
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
NUM_RETRIES = 200


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

    write_to_file(
        public_dns_names=get_public_dns_names_cloudformation_stack(opts.stackname),
        private_dns_names=get_private_dns_names_cloudformation_stack(opts.stackname),
        ip_to_ansible_group=ip_to_ansible_group_for_cloudformation_stack(opts.stackname),
        filename=opts.targetfile,
    )

    print("Generated {}".format(opts.targetfile))


def get_running_instances_for_cloudformation_stack(stackname):

    """
    Blocks until CloudFormation stack is fully up and running and all EC2 instances
    are listening on port 22.

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

    return instances_for_stack


def get_public_dns_names_cloudformation_stack(stackname):

    """
    Returns the public DNS names of all EC2 instances in the stack
    """

    instances_for_stack = get_running_instances_for_cloudformation_stack(stackname)

    # get public_dns_name for all instances
    return get_public_dns_names(instances_for_stack)


def get_private_dns_names_cloudformation_stack(stackname):

    instances_for_stack = get_running_instances_for_cloudformation_stack(stackname)

    return get_private_dns_names(instances_for_stack)


def ip_to_ansible_group_for_cloudformation_stack(stackname):

    """
    Generate a dictionary like:

    "ip_to_node_type": {
       "s61702cnt72.sc.couchbase.com": "couchbase_servers",
       "s61703cnt72.sc.couchbase.com": "couchbase_servers",
       "s61704cnt72.sc.couchbase.com": "couchbase_servers",
       "s61705cnt72.sc.couchbase.com": "sync_gateways",
       ....
    }
    """

    instances_for_stack = get_running_instances_for_cloudformation_stack(stackname)

    ip_to_ansible_group = {}
    for instance in instances_for_stack:
        ansible_group = get_ansible_group_for_instance(instance)
        ip_to_ansible_group[instance.public_dns_name] = ansible_group

    return ip_to_ansible_group


def get_ansible_group_for_instance(instance):

    """
    Given an ec2 instance:

    1. Look for the "type" tag, which will be something like "couchbaserver", which is set in cloudformation template
    2. Translate that to the expected "node_type" that corresponds to ansible group

    NOTE regarding sg_accels:  they are tagged with type=syncgateway, but they also have a CacheType="writer" tag
    that we can use to differentiate them from sync gateways

    """

    instance_type_to_ansible_group = {
        "couchbaseserver": "couchbase_servers",
        "syncgateway": "sync_gateways",
        "gateload": "load_generators",
        "loadbalancer": "load_balancers",
        "loadgenerator": "load_generators",  # forwards compatibility in case we rename this from "gateload" -> "loadgenerator"
        "unknown": "unknown",
    }

    if 'Type' not in instance.tags:
        instance_type = "unknown"
    else:
        instance_type = instance.tags['Type']

    if instance_type == "syncgateway":
        # Deal with special case for sg accels
        if 'CacheType' in instance.tags:
            return "sg_accels"

    return instance_type_to_ansible_group[instance_type]


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
            if stack_event.resource_type == "AWS::CloudFormation::Stack":
                if stack_event.resource_status in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
                    print("Stack {} has successfully been created/updated".format(stackname))
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


def get_private_dns_names(instances):

    return [instance.private_dns_name for instance in instances]


def write_to_file(public_dns_names, private_dns_names, ip_to_ansible_group, filename):
    """
    {
        "ip_to_node_type": {
            "s61702cnt72.sc.couchbase.com": "couchbase_servers",
            "s61703cnt72.sc.couchbase.com": "couchbase_servers",
            "s61704cnt72.sc.couchbase.com": "couchbase_servers",
            "s61705cnt72.sc.couchbase.com": "sync_gateways",
            ....
        }
        "ips": [
            "ec2-54-242-119-83.compute-1.amazonaws.com",
            "ec2-54-242-119-84.compute-1.amazonaws.com",
        ]
    }
    """
    output_dictionary = {
        "ip_to_node_type": ip_to_ansible_group,
        "private_dns_names": private_dns_names,
        "ips": public_dns_names,
    }

    with open(filename, 'w') as target:
        target.write(json.dumps(output_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))


if __name__ == "__main__":

    main()
