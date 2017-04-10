#!/usr/bin/env bash

# Create an ansible config from template
mv ansible.cfg.example ansible.cfg

# Change default 'vagrant' user to 'root' for docker
sed -i 's/remote_user = vagrant/remote_user = root/' ansible.cfg

pool_file="resources/pool.json"
touch ${pool_file}

pool='{"ips":["host1","host2","host3","host4","host5"]}'
echo ${pool} > ${pool_file}

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py