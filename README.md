
This folder is essentially a rewrite-from-scratch of the encompassing repo with the following differences:

* Uses python rather than node.js for tests
* Uses ansible for provisioning and cluster orchestration

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
