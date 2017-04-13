## Pull base image for cluster target containers

Based off of https://github.com/alvaroaleman/docker-centos7-systemd-sshd/blob/master/Dockerfile

sshd and systemd are currently required to run the sync gateway functional tests

```
$ docker pull sethrosetter/centos7-systemd-sshd
```
