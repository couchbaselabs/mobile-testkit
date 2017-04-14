### Running tests with docker image

IMPORTANT: This will copy your public / and private key to allow ssh access from mobile-testkit container to other clusters in the container.

```
python docker/create_cluster.py --network-name cbl --number-of-nodes 5 --path-to-public-key ~/.ssh/id_rsa.pub --clean
```

TODO: Automate this
```
docker exec -it mobile-testkit /bin/bash
./run_sg_tests.sh
```


## Capturing network traffic

From the **Linux Host** where docker is running

```
$ yum install -y tcpdump
$ tcpdump -i docker0 -w /tmp/docker.pcap port 4984
^C
```

Now, get the file to your OSX host and open it in Wireshark.  It should contain all HTTP traffic between the test suite and the sync gateway machines.
