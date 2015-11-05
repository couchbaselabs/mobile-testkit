
This folder is essentially a rewrite-from-scratch of the encompassing repo with the following differences:

* Uses python rather than node.js for tests
* Uses ansible for provisioning and cluster orchestration

## Run locally

You will need several dependencies installed, which are documented in the `docker/controller/Dockerfile`.

## Run under docker

See `docker/controller/README.md`

## Provision Cluster (one time only)

Example:

```
$ python prov/provision_cluster.py --server-version=3.1.1 --sync-gateway-branch=feature/distributed_index_bulk_set
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