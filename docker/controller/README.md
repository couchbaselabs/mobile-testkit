
## Run docker image

```
$ docker run -ti tleyden5iwx/sync-gateway-testcluster /bin/bash
```

The rest of the steps should be run **inside** the running docker container.

## Clone repo

```
$ cd /opt
$ git clone https://github.com/couchbaselabs/sync-gateway-tests.git
$ cd sync-gateway-tests/distributed_index_tests
```

## Create Ansible Inventory and push ssh keys

```
$ ssh-keygen
$ python conf/ini_to_ansible_host.py  --install-keys=id_rsa --ini-file=conf/hosts.ini
```

## Running tests

See `distributed_index_tests/README.md` in this repo for more information

## Capturing network traffic

From the **Linux Host** where docker is running

```
$ yum install -y tcpdump
$ tcpdump -i docker0 -w /tmp/docker.pcap port 4984
^C
```

Now, get the file to your OSX host and open it in Wireshark.  It should contain all HTTP traffic between the test suite and the sync gateway machines.
