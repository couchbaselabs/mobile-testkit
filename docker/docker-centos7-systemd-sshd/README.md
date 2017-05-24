## Pull base image for cluster target containers

sshd and systemd are currently required to run the sync gateway functional tests

```
$ docker pull sethrosetter/centos7-systemd-sshd
```

## To run
```
$ docker run -d --privileged --name centos-7-systemd-sshd -v /sys/fs/cgroup:/sys/fs/cgroup:ro -p 6666:22 sethrosetter/centos7-systemd-sshd
```

## To ssh
```
$ docker cp ~/.ssh/id_rsa.pub centos-7-systemd-sshd:/root/.ssh/authorized_keys
$ ssh root@localhost -p 6666
```

## Monitoring network traffic on the container
```
# Use whatever port you wish to be monitoring
$ ngrep -W byline -d eth1 port 4984 or port 4985
```
