
## Run docker image

```
docker run -e AWS_KEY=your_key -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=".." local/mobile-testkit python libraries/provision/create_and_instantiate_cluster.py     --stackname="TestMTKDocker"     --num-servers=1     --server-type="m3.medium"     --num-sync-gateways=1     --sync-gateway-type="m3.medium"     --num-gatlings=1     --gatling-type="m3.medium"     --num-lbs=0     --lb-type="m3.medium"
```


## Capturing network traffic

From the **Linux Host** where docker is running

```
$ yum install -y tcpdump
$ tcpdump -i docker0 -w /tmp/docker.pcap port 4984
^C
```

Now, get the file to your OSX host and open it in Wireshark.  It should contain all HTTP traffic between the test suite and the sync gateway machines.
