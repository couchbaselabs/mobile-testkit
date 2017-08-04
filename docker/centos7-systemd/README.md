## Pull base image for cluster target containers

systemd is currently required to run the sync gateway functional tests

```
$ docker pull couchbase/centos7-systemd
```

## Monitoring network traffic on the container
```
# Use whatever port you wish to be monitoring
$ ngrep -W byline -d eth1 port 4984 or port 4985
```
