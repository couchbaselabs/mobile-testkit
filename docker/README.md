## Creating a cluster

This will create a network 'cbl' and create 7 containers in the 'cbl' network.
All containers will be able to communicate with others in the network.

```
python docker/cluster.py --create --network-name cbl --number-of-nodes 7 --path-to-public-key ~/.ssh/id_rsa.pub --pull
```

### Local dev

Passing a `--dev` flag will provide some additional functionality.
It will set up the following:
- A mapping between common log file locations and your local /tmp folder will be setup. This will allow for easier debugging
- Port mapping will be setup to allow inspection of running services via local host. The mapping will be written to `portmaps.json` for reference 

```
python docker/cluster.py --create --network-name cbl --number-of-nodes 7 --path-to-public-key ~/.ssh/id_rsa.pub --pull --dev
```

## Destroying a cluster

This will remove all of the containers in the 'cbl' network and remove the 'cbl' network

```
python docker/cluster.py --destroy --network-name cbl
```

### Cleaning and starting over

WARNING!!! This will remove all you containers / network running locally. Use with caution.

Remove all running containers
```
docker rm -f $(docker ps -a -q)
```

Remove all networks
```
docker network rm $(docker network ls)
```