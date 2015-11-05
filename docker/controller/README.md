
## Run docker image

```
$ docker run -ti tleyden5iwx/sync-gateway-tests /bin/bash
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

## Run all tests

```
$ ./test
```

## Run single test

```
$ python -m pytest tests/<testfile>.py
```
