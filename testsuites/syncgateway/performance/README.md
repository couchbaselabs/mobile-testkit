=== Running Performance Tests

- <<Spin Up Machines on AWS>>

- Generate a pool.json

```
python libraries/provision/generate_pools_json_from_aws.py --stackname=TleydenPerfSyncGw12 --targetfile=resources/pool.json
```

- Generate clusters from pool

This will create the `2sg_3cbs_2lgs` and `2sg_3cbs_2lgs.json` cluster config that is used for performance testing

```
python libraries/utilities/generate_clusters_from_pool.py
```

- Set CLUSTER_CONFIG

```
export CLUSTER_CONFIG=resources/cluster_configs/2sg_3cbs_2lgs
```

- Provision cluster and install dependencies

```
python libraries/provision/provision_cluster.py --install-deps --server-version 4.1.1 --sync-gateway-version 1.3.0-274 
```

- Run tests

```
python testsuites/syncgateway/performance/run_perf_test.py --number-pullers 1000 --number-pushers 1000 --use-gateload --test-id 1 --sync-gateway-config-path resources/sync_gateway_configs/performance/sync_gateway_default_performance_cc.json
```
