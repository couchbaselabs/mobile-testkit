
# Python script to generate the cloudformation template json file
# This is not strictly needed, but it takes the pain out of writing a
# cloudformation template by hand.  It also allows for DRY approaches
# to maintaining cloudformation templates.

from troposphere import Ref, Template, Parameter, Output, Join, GetAtt, Tags
import troposphere.ec2 as ec2


def gen_template(config):

    num_couchbase_servers = config.server_number
    couchbase_instance_type = config.server_type

    num_sync_gateway_servers = config.sync_gateway_number
    sync_gateway_server_type = config.sync_gateway_type

    num_gateloads = config.load_number
    gateload_instance_type = config.load_type

    t = Template()
    t.add_description(
        'An Ec2-classic stack with Couchbase Server, Sync Gateway + load testing tools '
    )

    def createCouchbaseSecurityGroups(t):

        # Couchbase security group
        secGrpCouchbase = ec2.SecurityGroup('CouchbaseSecurityGroup')
        secGrpCouchbase.GroupDescription = "Allow access to Couchbase Server"
        secGrpCouchbase.SecurityGroupIngress = [
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="22",
                ToPort="22",
                CidrIp="0.0.0.0/0",
            ),
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="8091",
                ToPort="8091",
                CidrIp="0.0.0.0/0",
            ),
            ec2.SecurityGroupRule(   # sync gw user port
                IpProtocol="tcp",
                FromPort="4984",
                ToPort="4984",
                CidrIp="0.0.0.0/0",
            ),
            ec2.SecurityGroupRule(   # sync gw admin port
                IpProtocol="tcp",
                FromPort="4985",
                ToPort="4985",
                CidrIp="0.0.0.0/0",
            ),
            ec2.SecurityGroupRule(   # expvars
                IpProtocol="tcp",
                FromPort="9876",
                ToPort="9876",
                CidrIp="0.0.0.0/0",
            )
        ]

        # Add security group to template
        t.add_resource(secGrpCouchbase)

        cbIngressPorts = [
            {"FromPort": "4369", "ToPort": "4369" },    # couchbase server
            {"FromPort": "5984", "ToPort": "5984" },    # couchbase server
            {"FromPort": "8092", "ToPort": "8092" },    # couchbase server
            {"FromPort": "11209", "ToPort": "11209" },  # couchbase server
            {"FromPort": "11210", "ToPort": "11210" },  # couchbase server
            {"FromPort": "11211", "ToPort": "11211" },  # couchbase server
            {"FromPort": "21100", "ToPort": "21299" },  # couchbase server
        ]

        for cbIngressPort in cbIngressPorts:
            from_port = cbIngressPort["FromPort"]
            to_port = cbIngressPort["ToPort"]
            name = 'CouchbaseSecurityGroupIngress{}'.format(from_port)
            secGrpCbIngress = ec2.SecurityGroupIngress(name)
            secGrpCbIngress.GroupName = Ref(secGrpCouchbase)
            secGrpCbIngress.IpProtocol = "tcp"
            secGrpCbIngress.FromPort = from_port
            secGrpCbIngress.ToPort = to_port
            secGrpCbIngress.SourceSecurityGroupName = Ref(secGrpCouchbase)
            t.add_resource(secGrpCbIngress)

        return secGrpCouchbase


    #
    # Parameters
    #
    keyname_param = t.add_parameter(Parameter(
        'KeyName', Type='String',
        Description='Name of an existing EC2 KeyPair to enable SSH access'
    ))

    secGrpCouchbase = createCouchbaseSecurityGroups(t)

    # Couchbase Server Instances
    for i in xrange(num_couchbase_servers):
        name = "couchbaseserver{}".format(i)
        instance = ec2.Instance(name)
        instance.ImageId = "ami-96a818fe"  # centos7
        instance.InstanceType = couchbase_instance_type
        instance.SecurityGroups = [Ref(secGrpCouchbase)]
        instance.KeyName = Ref(keyname_param)
        instance.Tags=Tags(Name=name, Type="couchbaseserver")

        instance.BlockDeviceMappings = [
            ec2.BlockDeviceMapping(
                DeviceName = "/dev/sda1",
                Ebs = ec2.EBSBlockDevice(
                    DeleteOnTermination = True,
                    VolumeSize = 60,
                    VolumeType = "gp2"
                )
            )
        ]
        t.add_resource(instance)

    # Sync Gw instances (ubuntu ami)
    for i in xrange(num_sync_gateway_servers):
        name = "syncgateway{}".format(i)
        instance = ec2.Instance(name)
        instance.ImageId = "ami-96a818fe"  # centos7
        instance.InstanceType = sync_gateway_server_type
        instance.SecurityGroups = [Ref(secGrpCouchbase)]
        instance.KeyName = Ref(keyname_param)
        instance.BlockDeviceMappings = [
            ec2.BlockDeviceMapping(
                DeviceName = "/dev/sda1",
                Ebs = ec2.EBSBlockDevice(
                    DeleteOnTermination = True,
                    VolumeSize = 60,
                    VolumeType = "gp2"
                )
            )
        ]

        # Make syncgateway0 a cache writer, and the rest cache readers
        # See https://github.com/couchbase/sync_gateway/wiki/Distributed-channel-cache-design-notes
        if i == 0:
            instance.Tags=Tags(Name=name, Type="syncgateway", CacheType="writer")
        else:
            instance.Tags=Tags(Name=name, Type="syncgateway")

        t.add_resource(instance)

    # Gateload instances (ubuntu ami)
    for i in xrange(num_gateloads):
        name = "gateload{}".format(i)
        instance = ec2.Instance(name)
        instance.ImageId = "ami-96a818fe"  # centos7
        instance.InstanceType = gateload_instance_type
        instance.SecurityGroups = [Ref(secGrpCouchbase)]
        instance.KeyName = Ref(keyname_param)
        instance.Tags=Tags(Name=name, Type="gateload")
        instance.BlockDeviceMappings = [
            ec2.BlockDeviceMapping(
                DeviceName = "/dev/sda1",
                Ebs = ec2.EBSBlockDevice(
                    DeleteOnTermination = True,
                    VolumeSize = 20,
                    VolumeType = "gp2"
                )
            )
        ]

        t.add_resource(instance)

    return t.to_json()


