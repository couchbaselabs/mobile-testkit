
This repository contains:

* Sync Gateway + Couchbase Server Cluster setup scripts suitable for:
    * Functional Tests
    * Performance Tests
* Functional Test Suite (python)

## Setup Controller

### Start a container

```shell
$ docker run -ti tleyden5iwx/sync-gateway-tests /bin/bash
```

The rest of the commands should be run **inside** the container created in the previous step.

### Clone Repo

```
$ cd /opt
$ git clone https://github.com/couchbaselabs/sync-gateway-testcluster.git
```

### Copy SSH key from Host -> Container

In order to be able to ssh from your container into any of the hosts on AWS using public key auth, which is required to run most of the ansible commands, you will need to have an ssh keypair in your container that corresponds to your registered AWS key.


## Setup Cluster

### Spin up VM's or Bare Metal machines

Requirements:

* Should have a centos user with full root access in /etc/sudoers

### Spin up Machines on AWS

**Add boto configuration**

```
$ cat >> ~/.boto
[Credentials]
aws_access_key_id = CDABGHEFCDABGHEFCDAB
aws_secret_access_key = ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
^D
```

(and replace fake credentials above with your real credentials)

**Add AWS env variables**

```
$ export AWS_ACCESS_KEY_ID=CDABGHEFCDABGHEFCDAB
$ export AWS_SECRET_ACCESS_KEY=ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
$ export AWS_KEY=<your-aws-keypair-name>
```

**To run tests or ansible scripts**

```
$ export KEYNAME=key_<your-aws-keypair-name>
```

**To gather data in Splunk you will want to set variable below**

```
$ export SPLUNK_SERVER="<url_of_splunk_server>:<port>"
$ export SPLUNK_SERVER_AUTH="<username>:<password>"
```

**To kick off cluster**

```
python create_and_instantiate_cluster.py 
    --stackname="YourCloudFormationStack"
    --num-servers=2
    --server-type="m3.large"
    --num-sync-gateways=1
    --sync-gateway-type="m3.medium"
    --num-gatlings=1
    --gatling-type="m3.medium"
```

This script performs a series of steps for you

1) It uses [troposphere](https://github.com/cloudtools/troposphere) to generate the Cloudformation template (a json file). The Cloudformation config is declared via a Python DSL, which then generates the Cloudformation Json.

2) The generated template is uploaded to AWS with ssh access to the AWS_KEY name you specified (assuming that you have set up that keypair in AWS prior to this)

## Manually generate conf/hosts.ini (AWS only)

If you are running on AWS, you will need to manually generate a conf/hosts.ini file so that the provisioning scripts have a working Ansible Inventory to use.  Eventually, this step will be automated.

* Open conf/hosts.ini
* Go to the AWS console and find the public hostnames of your servers
* Update conf/hosts.ini with these hostnames, depending on their respective roles
* Save the conf/hosts.ini file

## Setup hosts / deploy shared key

This will generate a 'temp_ansible_hosts' file from a conf/host-file-name.ini that will be used in provisioning and running tests.
If you change want to changes your cluster definition, you must rerun this to regenerate the ansible host file.

```
python conf/ini_to_ansible_host.py --ini-file=conf/hosts.ini
```

One time only. Ansible playbooks require ssh access to run on the target hosts. 
This script will attempt to install a common public key to ~/.ssh/knownhosts on the machines in the cluster via ssh-copy-id. 

```
~/.ssh » ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/Users/sethrosetter/.ssh/id_rsa):<test-key>
```

Generate the ansible hosts file and attempt to install the shared key on all machines in the cluster

```
python conf/ini_to_ansible_host.py --ini-file=conf/hosts.ini --install-key=<test-key>.pub --ssh-user=<user>
```

## Set your user

If your ssh user is different then root, you may need to edit prov/ansible/ansible.cfg

## Provision Cluster 

Example:

```
$ python prov/provision_cluster.py --server-version=3.1.1 --sync-gateway-branch=feature/distributed_index_bulk_set
```

If you experience ssh errors, you may need to verify that the key has been added to your ssh agent

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/<test-key>
```

## Run Functional Tests

## Run Performance Tests



*********************************************************************************

# perfcluster-aws README

## Install pre-requisites

**Install PIP**

```
$ sudo easy_install pip
```

**Python Dependencies**

```
$ sudo pip install ansible
$ sudo pip install boto
$ sudo pip install troposphere
$ sudo pip install awscli
```

Alternatively, you can use the [Docker image](https://github.com/couchbaselabs/perfcluster-aws/wiki/Running-under-Docker) which has all the pre-requisites pre-installed.

**Add boto configuration**

```
$ cat >> ~/.boto
[Credentials]
aws_access_key_id = CDABGHEFCDABGHEFCDAB
aws_secret_access_key = ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
^D
```

(and replace fake credentials above with your real credentials)

**Add AWS env variables**

```
$ export AWS_ACCESS_KEY_ID=CDABGHEFCDABGHEFCDAB
$ export AWS_SECRET_ACCESS_KEY=ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
$ export AWS_KEY=<your-aws-keypair-name>
```

**To run tests or ansible scripts**

```
$ export KEYNAME=key_<your-aws-keypair-name>
```

**To gather data in Splunk you will want to set variable below

```
$ export SPLUNK_SERVER="<url_of_splunk_server>:<port>"
$ export SPLUNK_SERVER_AUTH="<username>:<password>"
```

## Install steps 

`cd scripts` to get into the scripts subdirectory.

### Creates topology and starts the Cloudformation stack on AWS

```
python create_and_instantiate_cluster.py 
    --stackname="YourCloudFormationStack"
    --num-servers=2
    --server-type="m3.large"
    --num-sync-gateways=1
    --sync-gateway-type="m3.medium"
    --num-gatlings=1
    --gatling-type="m3.medium"
```

This script performs a series of steps for you

1) It uses [troposphere](https://github.com/cloudtools/troposphere) to generate the Cloudformation template (a json file). The Cloudformation config is declared via a Python DSL, which then generates the Cloudformation Json.

2) The generated template is uploaded to AWS with ssh access to the AWS_KEY name you specified (assuming that you have set up that keypair in AWS prior to this)

### Provision the cluster

Install Couchbase Server and build sync_gateway from source with optional --branch (master is default).
Additionally, you can provide an optional custom sync_gateway_config.json file. If this is not specified, it will use the config in "perfcluster-aws/ansible/playbooks/files/sync_gateway_config.json"

```
python provision_cluster.py 
    --server-version=3.1.0
    --sync-gateway-branch="feature/distributed_cache_stale_ok"
    --sync-gateway-config-file="<absolute path to your sync_gateway_config.json file>" (optional)
```

(IN PROGRESS) Install Couchbase Server and download sync_gateway binary (1.1.1 is default)

```
python provision_cluster.py 
    --server-version=3.1.0
    --sync-gateway-version=1.1.1
    --sync-gateway-build=10
```

### Install Couchbase Server

Will install Couchbase Server in the cluster on all couchbase server nodes

```
python install_couchbase_server.py
    --version=<couchbase_server_version>
    --build-number=<server_build_number>
```

### Install sync_gateway

Will install sync_gateway in the cluster on all sync_gateway nodes. Uses perfcluster-aws/ansible/playbooks/files/sync_gateway_config.json by default

From source

```
python install_sync_gateway.py
    --branch=<sync_gateway_branch_to_build>
    --config-file-path=<path_to_local_sync_gateway_config> (optional)
```

or from release (IN PROGRESS)

```
python install_sync_gateway.py
    --version=<couchbase_server_version>
    --build-number=<server_build_number>
    --config-file-path=<path_to_local_sync_gateway_config> (optional)
```

### Setup and run gatling tests

```
python run_tests.py
    --number-pullers=0
    --number-pushers=7500
```

### Setup and run gateload tests

Currently the load generation is specified in ansible/files/gateload_config.json.
(In progress) Allow this to be parameterized

```
python run_tests.py
    --use-gateload
```

### Restart sync_gateway

The following command will execute a few steps

1) Flush bucket-1 and bucket-2 in Couchbase Server

2) Stop running sync_gateway services

3) Remove sync_gateway logs

4) Restart sync_gateway services

```
python reset_sync_gateway.py
```

### Kill gateload

The following command will kill running gateload processes

```
python kill_gateload.py
```

### Teardown cluster

```
 python teardown_cluster.py 
    --stackname="YourCloudFormationStack"
```

### Distributed index branch testing note

If you are testing the Sync Gateway distributed index branch, one extra step is needed:

```
ansible-playbook -l $KEYNAME configure-sync-gateway-writer.yml
```

### Starting Gateload tests

If you need to run Gateload rather than Gatling, do the following steps

```
$ cd ../..
$ python generate_gateload_configs.py  # generates and uploads gateload configs with correct SG IP / user offset
$ cd ansible/playbooks
$ ansible-playbook -l $KEYNAME start-gateload.yml
```

### View Gatelod test output

* Sync Gateway expvars on $HOST:4985/_expvar

* Gateload expvars $HOST:9876/debug/var

* Gateload expvar snapshots

    * ssh into gateload, and `ls expvar*` to see snapshots

    * ssh into gateload, and run `screen -r gateload` to view gateload logs

## Viewing instances by type

To view all couchbase servers:

```
$ ansible tag_Type_couchbaseserver --list-hosts
```

The same can be done for Sync Gateways and Gateload instances.  Here are the full list of tag filters:

* tag_Type_couchbaseserver
* tag_Type_syncgateway
* tag_Type_gateload

## Collecting expvar output

```
while [ 1 ]
do
    outfile=$(date +%s)
    curl localhost:9876/debug/vars -o ${outfile}.json
    echo "Saved output to $outfile"
    sleep 60
done
```

## Collecting cpu/heap/profile reports

```
$ cd ansible/playbooks
$ ansible-playbook -l $KEYNAME collect-sync-gateway-profile.yml
```

## Viewing data on Splunk

First, you will need to [Install Splunk](https://github.com/couchbaselabs/perfcluster-aws/wiki/Setting-up-a-Splunk-Server) on a server somewhere.

Note: The data collected by the unix app is by default placed into a separate index called ‘os’ so it will not be searchable within splunk unless you either go through the UNIX app, or include the following in your search query: “index=os” or “index=os OR index=main” (don’t paste doublequotes)


# sync-gateway-tests README


## Run locally

You will need several dependencies installed, which are documented in the `docker/controller/Dockerfile`.

## Run under docker

See `docker/controller/README.md`

## Setup hosts / deploy shared key

This will generate a 'temp_ansible_hosts' file from a conf/host-file-name.ini that will be used in provisioning and running tests.
If you change want to changes your cluster definition, you must rerun this to regenerate the ansible host file.

```
python conf/ini_to_ansible_host.py --ini-file=conf/hosts.ini
```

One time only. Ansible playbooks require ssh access to run on the target hosts. 
This script will attempt to install a common public key to ~/.ssh/knownhosts on the machines in the cluster
via ssh-copy-id. 

On the test harness

```
~/.ssh » ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/Users/sethrosetter/.ssh/id_rsa):<test-key>
```

Generate the ansible hosts file and attempt to install the shared key on all machines in the cluster

```
python conf/ini_to_ansible_host.py --ini-file=conf/hosts.ini --install-key=<test-key>.pub --ssh-user=<user>
```

## Set your user

If your ssh user is different then root, you may need to edit prov/ansible/ansible.cfg

## Provision Cluster (one time only)

Example:

```
$ python prov/provision_cluster.py --server-version=3.1.1 --sync-gateway-branch=feature/distributed_index_bulk_set
```

If you experience ssh errors, you may need to verify that the key has been added to your ssh agent

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/<test-key>
```

## Running all tests

```
$ ./test
```

## Running an individual test

```
$ python -m pytest --capture=no tests/test_single_user_multiple_channels.py
```

## Collecting Sync Gateway logs

```
$ python prov/fetch_sg_logs.py
```
