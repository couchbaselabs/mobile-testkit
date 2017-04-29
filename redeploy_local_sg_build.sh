#!/usr/bin/env bash

if [ -z "$CLUSTER_CONFIG" ]; then
    echo "Need to set CLUSTER_CONFIG"
    exit 1
fi

parseOptions () {


    while getopts "b:h" opt; do
	case $opt in
	    b)
		BINARY_DIRECTORY=$OPTARG
		echo "Looking for sync gateway / accel binaries in : $BINARY_DIRECTORY"
		;;
	    h)
		echo "./redeploy_local_sg_build.sh -b /Users/tleyden/Development/sync_gateway/godeps/bin/linux_amd64/"
		echo "-b <binary_directory> the path where the linux binaries for sync_gateway and sync-gateway-accel"
		exit 0
		;;
	    \?)
		echo "Invalid option: -$OPTARG.  Aborting" >&2
		exit 1
		;;
	esac
    done

}

# Parse the getopt options and set variables
parseOptions "$@"

if [ -z "$BINARY_DIRECTORY" ]; then
    echo "Need to pass in -b flag to specify the directory which contains the Sync Gateway / Accel binaries.  Run with -h for help"
    exit 1
fi

SG_BINARY="$BINARY_DIRECTORY/sync_gateway"
SGA_BINARY="$BINARY_DIRECTORY/sync-gateway-accel"

ansible-playbook -i $CLUSTER_CONFIG libraries/provision/ansible/playbooks/redeploy-local-sg-build.yml --extra-vars "local_sg_binary=$SG_BINARY local_sga_binary=$SGA_BINARY"

