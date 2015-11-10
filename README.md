
This repository contains:

* Sync Gateway + Couchbase Server Cluster setup scripts suitable for:
    * Functional Tests
    * Performance Tests
* Functional Test Suite (python)

## Setup Controller

The "controller" is the machine that runs ansible, which is typically:

* Your developer workstation
* A virtual machine / docker container

The instructions below are docker specific, but if you look in `docker/controller/Dockerfile` it should give you an idea of the required dependencies if you want to make this work directly on your workstation.

### Start a Docker container for the Ansible Controller

First you will need to [install docker](https://docs.docker.com/mac/step_one/).

```shell
$ docker run -ti tleyden5iwx/sync-gateway-tests /bin/bash
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
$ cd sync-gateway-testcluster/provision
$ python create_and_instantiate_cluster.py \
    --stackname="YourCloudFormationStack" \
    --num-servers=1 \
    --server-type="m3.large" \
    --num-sync-gateways=1 \
    --sync-gateway-type="m3.medium" \
    --num-gatlings=1 \
    --gatling-type="m3.medium" 
```

The AWS virtual machines will be accessible via the `AWS_KEY` you specified above.

## Setup Ansible inventory

**AWS**

Manually create a `sync-gateway-testcluster/temp_ansible_hosts` file in this format, with the hosts listed in your AWS console:

```
[couchbase_servers]
ec2-54-205-165-155.compute-1.amazonaws.com ansible_ssh_host=ec2-54-205-165-155.compute-1.amazonaws.com

[sync_gateways]
ec2-54-158-112-128.compute-1.amazonaws.com ansible_ssh_host=ec2-54-158-112-128.compute-1.amazonaws.com

[load_generators]
ec2-54-163-112-228.compute-1.amazonaws.com ansible_ssh_host=ec2-54-163-112-228.compute-1.amazonaws.com
```

**Virutal Machines**

One time only. Ansible playbooks require ssh access to run on the target hosts.  This script will attempt to install a common public key to ~/.ssh/knownhosts on the machines in the cluster via ssh-copy-id. 

```
$ ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/Users/sethrosetter/.ssh/id_rsa):<test-key>
```

Generate the ansible hosts file and attempt to install the shared key on all machines in the cluster

```
python conf/ini_to_ansible_host.py --ini-file=conf/hosts.ini --install-key=<test-key>.pub --ssh-user=<user>
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
$ python provision/provision_cluster.py --server-version=3.1.1 --sync-gateway-branch=feature/distributed_index_bulk_set
```

Example from a pre-built version (dev build):

```
$ python provision/provision_cluster.py --server-version=3.1.1 --sync-gateway-dev-build-url=feature/distributed_index --sync-gateway-dev-build-number=345
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
$ python provision/install_splunk.py
```

## Run Performance Tests

**Gateload**

```
python run_tests.py
    --use-gateload
    --gen-gateload-config
```

**Gatling**

NOTE: this is currently broken

```
python run_tests.py
    --number-pullers=0
    --number-pushers=7500
```

### Performance test data

Most of the performance test data will be pushed to Splunk (if the splunk forwarder is installed), but you can download the Heap + CPU profile data via:

```
$ ansible-playbook performance_tests/ansible/playbooks/collect-sync-gateway-profile.yml -i temp_ansible_hosts
```

## Run Functional Tests

```
$ ./test
```

