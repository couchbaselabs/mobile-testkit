#!/usr/bin/env bash

# set python env
currentdir=`pwd`
export PYTHONPATH=${PYTHONPATH}:${currentdir}/
export ANSIBLE_CONFIG=${currentdir}/ansible.cfg

pool_file="resources/pool.json"
touch ${pool_file}

pool='{"ips":["host1","host2","host3","host4","host5"]}'
echo ${pool} > ${pool_file}

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py