FROM centos/systemd

MAINTAINER "Seth Rosetter" <seth.rosetter@gmail.com>

RUN yum -y install openssh-server; systemctl enable sshd.service

RUN mkdir -p /root/.ssh/

EXPOSE 22

CMD ["/usr/sbin/init"]