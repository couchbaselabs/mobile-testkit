#!/usr/bin/env bash
# perf cluster spin up

# Assumptions:
#	1 gatling per IR sync_gateway

# 1000b docs
# 5k writers per cluster
# 5k readers per cluster

#################
## 5k / 5k
#################

# 5est 4
# 8 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=9 --sync-gateway-type="c3.2xlarge" --num-gatlings=8 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 8 IR - 5000 / 8 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=625 --number-pullers=625  --test-id="5k-5k-8IR-1IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down four gateloads

# Test 4
# 4 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=5 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 5000 / 4 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250  --test-id="5k-5k-4IR-1IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 3
# 3 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=4 --sync-gateway-type="c3.2xlarge" --num-gatlings=3 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1667 --number-pullers=1667  --test-id="5k-5k-3IR-1IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 2
# 2 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500 --test-id="5k-5k-2IR-1IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 1
# 1 IR / 1 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=2 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 1 gateload node (5k pushers / 5k pullers)
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000 --test-id="5k-5k-1IR-1IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

## REPROVISION

# Test 10
# 8 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=10 --sync-gateway-type="c3.2xlarge" --num-gatlings=8 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 8 IR - 5000 / 8 = 625 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=625 --number-pullers=625  --test-id="5k-5k-8IR-2IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down four gateloads

# Test 9
# 4 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=6 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 5000 / 4 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250 --test-id="5k-5k-4IR-2IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 8
# 3 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=5 --sync-gateway-type="c3.2xlarge" --num-gatlings=3 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1667 --number-pullers=1667 --test-id="5k-5k-3IR-2IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 7
# 2 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=4 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 5000 / 2 = 2500 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500 --test-id="5k-5k-2IR-2IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down one gateload

# Test 6
# 1 IR / 2 IW
python provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="provisioning_config"
# Edit provisioning_config to reflect the number of writers you require
python provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000 --test-id="5k-5k-1IR-2IW"
python provision/teardown_cluster.py --stackname="SethPerfStack"







