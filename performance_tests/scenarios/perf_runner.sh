#!/usr/bin/env bash
# perf cluster spin up

# Assumptions:
#	1 gatling per IR sync_gateway

# 1000b docs
# 5k writers per cluster
# 5k readers per cluster

# Test 1
# 1 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=2 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
# 1 gateload node (5k pushers / 5k pullers)
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Test 2
# 2 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Test 3
# 3 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=4 --sync-gateway-type="c3.2xlarge" --num-gatlings=3 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1667 --number-pullers=1667
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Test 4
# 4 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=5 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
# 4 IR - 5000 / 4 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250
python provision/teardown_cluster.py --stackname="SethPerfStack"


# Test 5
# 1 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000
python provision/teardown_cluster.py --stackname="SethPerfStack"


# Test 6
# 2 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=4 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
# 4 IR - 5000 / 2 = 2500 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500
python provision/teardown_cluster.py --stackname="SethPerfStack"


# Test 7
# 3 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=5 --sync-gateway-type="c3.2xlarge" --num-gatlings=3 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1667 --number-pullers=1667
python provision/teardown_cluster.py --stackname="SethPerfStack"


# Test 8
# 4 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=6 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-branch=feature/distributed_index --install-deps
# 4 IR - 5000 / 4 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250
python provision/teardown_cluster.py --stackname="SethPerfStack"



