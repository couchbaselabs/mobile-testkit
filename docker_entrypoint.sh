#!/usr/bin/env bash

# Create an ansible config from template
mv ansible.cfg.example ansible.cfg

# Change default 'vagrant' user to 'root' for docker
sed -i 's/remote_user = vagrant/remote_user = root/' ansible.cfg

# Copy mounted pool.json location where testkit can see it
mv /tmp/pool.json resources/pool.json

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py

# Run single test
pytest pytest -s --mode=cc --server-version=4.6.1 --sync-gateway-version=1.4.0.2-3 -k "test_attachment_revpos_when_ancestor_unavailable" testsuites/syncgateway/functional/tests