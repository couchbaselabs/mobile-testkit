#!/usr/bin/env bash
# perf cluster spin up

# Assumptions:
#	1 gateload per IR sync_gateway

# 1000b docs
# 5k writers per cluster
# 5k readers per cluster

#################
## 10k / 10k
#################

# Test 4
# 8 IR / 1 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=9 --sync-gateway-type="c3.2xlarge" --num-gatlings=8 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 5000 / 4 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250 --test-id="10k-10k-8IR-1IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 4 gateloads and 4 sync_gateways

# Test 3
# 4 IR / 1 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=5 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500 --test-id="10k-10k-4IR-1IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 2 gateloads and 2 sync_gateways

# Test 2
# 2 IR / 1 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000 --test-id="10k-10k-2IR-1IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 1 gateload and 1 sync_gateway

# Test 1
# 1 IR / 1 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=2 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 1 gateload node (5k pushers / 5k pullers)
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=10000 --number-pullers=10000 --test-id="10k-10k-1IR-1IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"


## REPROVISION

# Test 8
# 8 IR / 2 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=10 --sync-gateway-type="c3.2xlarge" --num-gatlings=8 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 10000 / 8 = 1250 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=1250 --number-pullers=1250 --test-id="10k-10k-8IR-2IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 4 gateloads and 4 sync_gateways and edit provisioning config according

# Test 7
# 4 IR / 2 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=6 --sync-gateway-type="c3.2xlarge" --num-gatlings=4 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 10000 / 4 = 2500 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=2500 --number-pullers=2500 --test-id="10k-10k-4IR-2IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 2 gateloads and 2 sync_gateway and edit provisioning config according

# Test 6
# 2 IR / 2 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=4 --sync-gateway-type="c3.2xlarge" --num-gatlings=2 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 10000 / 2 = 5000 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=5000 --number-pullers=5000 --test-id="10k-10k-2IR-2IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"

# Take down 1 gateload and 1 sync_gateway and edit provisioning config according

# Test 5
# 1 IR / 2 IW
python libraries/provision/create_and_instantiate_cluster.py --stackname="SethPerfStack" --num-servers=3 --server-type="c3.2xlarge" --num-sync-gateways=3 --sync-gateway-type="c3.2xlarge" --num-gatlings=1 --gatling-type="c3.2xlarge"
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="SethPerfStack" --targetfile="aws_perf_config"
# Edit provisioning_config to reflect the number of writers you require
python libraries/provision/provision_cluster.py --server-version=4.1.0 --sync-gateway-version=1.2.0-XX --install-deps
# 4 IR - 10000 / 1 = 10000 readers and writers per sync_gateway IR
python performance_tests/run_tests.py --use-gateload --gen-gateload-config --reset-sync-gw --number-pushers=10000 --number-pullers=10000 --test-id="10k-10k-1IR-2IW"
python libraries/provision/teardown_cluster.py --stackname="SethPerfStack"







