import sys
import json
import os
import subprocess
from optparse import OptionParser

import cloudformation_template


class ClusterConfig:

    def __init__(self, name, server_number, server_type, sync_gateway_number, sync_gateway_type, load_number, load_type):

        self.__name = name
        self.__server_number = server_number
        self.__server_type = server_type
        self.__sync_gateway_number = sync_gateway_number
        self.__sync_gateway_type = sync_gateway_type
        self.__load_number = load_number
        self.__load_type = load_type

    @property
    def name(self):
        return self.__name

    @property
    def server_number(self):
        return self.__server_number

    @property
    def server_type(self):
        return self.__server_type

    @property
    def sync_gateway_number(self):
        return self.__sync_gateway_number

    @property
    def sync_gateway_type(self):
        return self.__sync_gateway_type

    @property
    def load_number(self):
        return self.__load_number

    @property
    def load_type(self):
        return self.__load_type

    def __validate_types(self):
        # Ec2 instances follow string format xx.xxxx
        # Hacky validation but better than nothing
        if not len(self.__server_type.split(".")) == 2:
            print "Invalid Ec2 server type"
            return False
        if not len(self.__sync_gateway_type.split(".")) == 2:
            print "Invalid Ec2 sync_gateway type"
            return False
        if not len(self.__load_type.split(".")) == 2:
            print "Invalid Ec2 load type"
            return False
        return True

    def __validate_numbers(self):
        # Validate against limits.json to prevent accidental giant AWS cluster
        with open("limits.json") as limits_config:
            limits = json.load(limits_config)
            if self.__server_number > limits["max_servers"]:
                print "You have exceed your maximum number of servers: {}".format(limits["max_servers"])
                print "Edit you limits.json file to override this behavior"
                return False
            if self.__sync_gateway_number > limits["max_sync_gateways"]:
                print "You have exceed your maximum number of servers: {}".format(limits["max_sync_gateways"])
                print "Edit you limits.json file to override this behavior"
                return False
            if self.__load_number > limits["max_loads"]:
                print "You have exceed your maximum number of servers: {}".format(limits["max_loads"])
                print "Edit you limits.json file to override this behavior"
                return False
            return True

    def is_valid(self):
        if not self.__name:
            print "Make sure you provide a stackname for your cluster."
            return False
        types_valid = self.__validate_types()
        numbers_within_limit = self.__validate_numbers()
        return types_valid and numbers_within_limit


def create_and_instantiate_cluster(config):

    print ">>> Creating cluster... "

    print ">>> Couchbase Server Instances: {}".format(config.server_number)
    print ">>> Couchbase Server Type:      {}".format(config.server_type)

    print ">>> Sync Gateway Instances:     {}".format(config.sync_gateway_number)
    print ">>> Sync Gateway Type:          {}".format(config.sync_gateway_type)

    print ">>> Load Instances:             {}".format(config.load_number)
    print ">>> Load Type:                  {}".format(config.load_type)

    print ">>> Generating Cloudformation Template"
    json = cloudformation_template.gen_template(config)

    template_file_name = "cloudformation_template.json"

    template_file = open(template_file_name, 'w')
    template_file.write(json)
    template_file.close()

    print ">>> Creating cluster on AWS"

    key = os.path.expandvars("$AWS_KEY")

    subprocess.call([
        "aws", "cloudformation", "create-stack",
        "--stack-name", config.name,
        "--region", "us-east-1",
        "--template-body", "file://{}".format(template_file_name),
        "--parameters", "ParameterKey=KeyName,ParameterValue={}".format(key)
    ])

if __name__ == "__main__":

    usage = """usage: python create_and_instantiate_cloud
        --stackname=<cluster_name>
        --num-servers=<number_couchbase_servers>
        --server-type=<ec2_instance_type>
        --num-sync-gateways <number_sync_gateways>
        --sync-gateway-type=<ec2_instance_type>
        --num-gatlings <number_gateloads>
        --gatling-type=<ec2_instance_type>"""

    parser = OptionParser(usage=usage)

    parser.add_option("", "--stackname",
                      action="store", type="string", dest="stackname",
                      help="name for your cluster")

    parser.add_option("", "--num-servers",
                      action="store", type="int", dest="num_servers", default=1,
                      help="number of couchbase server instances")

    parser.add_option("", "--server-type",
                      action="store", type="string", dest="server_type", default="m3.medium",
                      help="EC2 instance type for couchbase server")

    parser.add_option("", "--num-sync-gateways",
                      action="store", type="int", dest="num_sync_gateways", default=1,
                      help="number of sync_gateway instances")

    parser.add_option("", "--sync-gateway-type",
                      action="store", type="string", dest="sync_gateway_type", default="m3.medium",
                      help="EC2 instance type for sync_gateway type")

    parser.add_option("", "--num-gatlings",
                      action="store", type="int", dest="num_gatlings", default=1,
                      help="number of gatling instances")

    parser.add_option("", "--gatling-type",
                      action="store", type="string", dest="gatling_type", default="m3.medium",
                      help="EC2 instance type for gatling type")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    # Creates and validates cluster configuration
    cluster_config = ClusterConfig(
        opts.stackname,
        opts.num_servers,
        opts.server_type,
        opts.num_sync_gateways,
        opts.sync_gateway_type,
        opts.num_gatlings,
        opts.gatling_type
    )

    if not cluster_config.is_valid():
        print "Invalid cluster configuration. Exiting..."
        sys.exit(1)

    create_and_instantiate_cluster(cluster_config)

