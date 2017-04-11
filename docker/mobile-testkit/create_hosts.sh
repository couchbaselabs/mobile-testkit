#!/usr/bin/env bash

# Exit on error
set -e

# Create network
echo "Creating network: $1 with $2 nodes"
docker network create $1
docker network list

# Spin up the number node for this network
for i in $(seq 1 $2); do
    docker run --rm -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name host$i --network $1 sethrosetter/centos7-systemd-sshd
    docker cp $3 host$i:/root/.ssh/authorized_keys
done

# Start testkit docker image
docker run --rm -d --network cbl mobile-testkit

# TODO: Deploy key so that testkit has ssh access to the rest of the cluster

docker network inspect $1

