### Running tests with docker image

IMPORTANT: This will copy your public key to allow ssh access from mobile-testkit container to other clusters in the container.

```
$ python docker/create_cluster.py --network-name cbl --number-of-nodes 5 --path-to-public-key ~/.ssh/id_rsa.pub --clean
```

Mount local dev environment for iterative development with docker backend. This way you can make changes in your /{user}/mobile-testkit repo and execute within the context of the container.
```
$ docker run --rm -it --network=cbl --name=mobile-testkit -v /{user}/mobile-testkit:/opt/mobile-testkit -v /tmp/pool.json:/opt/mobile-testkit/resources/pool.json -v ~/.ssh/id_rsa:/root/.ssh/id_rsa test  /bin/bash
$ python libraries/utilities/generate_clusters_from_pool.py
$ pytest -s --mode=cc --server-version=4.6.1 --sync-gateway-version=1.4.0.2-3 testsuites/syncgateway/functional/tests
```

## Capturing network traffic

From the **Linux Host** where docker is running

```
$ yum install -y tcpdump
$ tcpdump -i docker0 -w /tmp/docker.pcap port 4984
^C
```

Now, get the file to your OSX host and open it in Wireshark.  It should contain all HTTP traffic between the test suite and the sync gateway machines.
