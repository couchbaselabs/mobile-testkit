#!/usr/bin/env bash

# Exit on error
set -e

# Create network
echo "Creating network: $1 with $2 nodes"
docker network create $1
docker network list

# Loop spin up the number node for this network
for i in $(seq 1 $2); do
    docker run --rm -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name host$i --network $1 alvaroaleman/centos7-systemd-sshd;
done

docker network inspect $1