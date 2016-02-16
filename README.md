
This repository contains:

* Sync Gateway + Couchbase Server Cluster setup scripts suitable for:
    * Functional Tests
    * Performance Tests
* Functional Test Suite (python)

## Setup Controller

The "controller" is the machine that runs ansible, which is typically:

* Your developer workstation
* A virtual machine / docker container

NOTE: This repo now only supports ansible 2.0+

The instructions below are docker specific, but if you look in `docker/controller/Dockerfile` it should give you an idea of the required dependencies if you want to make this work directly on your workstation.

### Start a Docker container for the Ansible Controller

First you will need to [install docker](https://docs.docker.com/mac/step_one/).

```shell
$ docker run -ti tleyden5iwx/sync-gateway-testcluster /bin/bash
```

The rest of the commands should be run **inside** the docker container created in the previous step.

### Clone Repo

```
$ cd /opt
$ git clone https://github.com/couchbaselabs/sync-gateway-testcluster.git
```

### Setup Global Ansible Config

```
$ cd sync-gateway-testcluster/provision/ansible/playbooks
$ cp ansible.cfg.example ansible.cfg
$ vi ansible.cfg  # edit to your liking
```

By default, the user is set to `root`, which works for VM clusters.  If you are on AWS, you will need to change that to `centos`

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
$ export KEYNAME=key_<your-aws-keypair-name>
```

You probably want to persist these in your `~/.bash_profile`.

**To kick off cluster**

```
$ python provision/create_and_instantiate_cluster.py \
    --stackname="YourCloudFormationStack" \
    --num-servers=1 \
    --server-type="m3.large" \
    --num-sync-gateways=2 \
    --sync-gateway-type="m3.medium" \
    --num-gatlings=1 \
    --gatling-type="m3.medium" \
    --num-lbs=0 \
    --lb-type="m3.medium" 
```

NOTE: currently need at least 2 sync gateways (1 sync gw and 1 sg_accel)

The AWS virtual machines will be accessible via the `AWS_KEY` you specified above.

If you want to install a load balancer in front of the Sync Gateway instances, set `--num-lbs` to 1.	

## Setup Ansible inventory

**AWS**

Generate the Ansible Inventory file (`provisioning_config`) via:

```
$ python provision/generate_ansible_inventory_from_aws.py \
     --stackname=YourCloudFormationStack \
     --targetfile=provisioning_config
```

## Configure sync gateway index readers vs index writers

Modify `provisioning_config` to remove at least one node from the `[sync_gateway_index_writers]` list

**Virtual Machines**

Create and edit your provisioning configuration
```
$ cp provisioning_config.example provisioning_config
```
Add the ip endpoints you would like to target

One time only. Ansible playbooks require ssh access to run on the target hosts.  This script will attempt to install a common public key to ~/.ssh/knownhosts on the machines in the cluster via ssh-copy-id. 

```
$ ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/Users/sethrosetter/.ssh/id_rsa):<test-key>
```

Attempt to install the shared key on all machines in the cluster defined in (`provisioning_config`)

```
python conf/install_keys.py \
  --key-name=<public-ssh-key-name> \
  --ssh-user=<user>
```

## SSH Key setup (AWS)

In order to use Ansible, the controller needs to have it's SSH keys in all the hosts that it's connecting to.  

Follow the instructions in [Docker container SSH key instructions](https://github.com/couchbaselabs/sync-gateway-testcluster/wiki/Docker-Container---SSH-Keys)

## Provision Cluster 

This step will install:

* 3rd party dependencies
* Couchbase Server
* Sync Gateway
* Gateload/Gatling load generators

Example building from source:

```
$ python provision/provision_cluster.py \
    --server-version=4.1.0 \
    --sync-gateway-branch=master
    --install-deps (first time only, this will install prerequisites to build / debug)
```

Example from a pre-built version (dev build):

```
$ python provision/provision_cluster.py \
    --server-version=3.1.1 \
    --sync-gateway-dev-build-url=feature/distributed_index \
    --sync-gateway-dev-build-number=345
    --install-deps (first time only, this will install prerequisites to build / debug)
```

Like all scripts, run `python provision/provision_cluster.py -h` to view help options.

If you experience ssh errors, you may need to verify that the key has been added to your ssh agent

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/<test-key>
```

## Install Splunk (optional)

**Set environment variables**

```
$ export SPLUNK_SERVER="<url_of_splunk_server>:<port>"
$ export SPLUNK_SERVER_AUTH="<username>:<password>"
```

**Install**

```
$ python provision/install_splunk_forwarder.py
```

## Run Performance Tests

**Gateload**

```
$ export PYTHONPATH=$PYTHONPATH:.
$ python performance_tests/run_tests.py --number-pullers 1000 --number-pushers 1000 --use-gateload --gen-gateload-config --reset-sync-gw --test-id="perftest" 
```

To stop the tests:

```
$ python performance_tests/kill_gateload.py
```

**Gatling**

```
$ export PYTHONPATH=$PYTHONPATH:.
$ python performance_tests/run_tests.py --number-pullers=1000 --number-pushers=1000
```

### Performance test data

Most of the performance test data will be pushed to Splunk (if the splunk forwarder is installed), but you can download the Heap + CPU profile data via:

```
$ ansible-playbook performance_tests/ansible/playbooks/collect-sync-gateway-profile.yml -i temp_ansible_hosts
```

## Run Functional tests

By default the logs from all of the sync_gateways will be zipped and placed in your /tmp directory if a test fails. You
can disable this behavior in functional_tests/settings

**Install dependencies (skip if using Docker container)**
```
pip install pytest
pip install futures
pip install requests
```

**Add current directory to $PYTHONPATH**

```
$ export PYTHONPATH=$PYTHONPATH:.
```

**Run all**
```
$ py.test -s
```
**Running a test fixture**
```
$ py.test -s "functional_tests/test_db_online_offline.py"
```
**Running an individual test**
```
$ py.test -s "functional_tests/test_db_online_offline.py::test_online_default_rest["CC-1"]"
```

## Monitoring the cluster
Make sure you have installed expvarmon 
```
go get github.com/divan/expvarmon
```

To monitor the Gateload expvars for [load_generators] nodes in the provisioning_config 
```
python utilities/monitor_gateload.py
```

To monitor the sync_gateway expvars for [sync_gateways] nodes in the provisioning_config 
```
python utilities/monitor_sync_gateway.py
```

## Collecting Sync Gateway logs

```
$ python utilities/fetch_sg_logs.py
```

## Reset Sync Gateway

```
$ ansible-playbook -i provisioning_config -u centos -e sync_gateway_config_filepath=../../../../conf/bucket_online_offline//bucket_online_offline_default_dcp_cc.json ./provision/ansible/playbooks/reset-sync-gateway.yml
```

*Note: replace the Sync Gateway config with the config that you need for your use case*

