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
