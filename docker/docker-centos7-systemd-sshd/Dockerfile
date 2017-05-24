FROM centos/systemd

MAINTAINER "Seth Rosetter" <seth.rosetter@gmail.com>

RUN yum -y update && \
    yum -y install epel-release && \
    yum -y install openssh-server sudo initscripts install ngrep install http;

RUN systemctl enable sshd.service

RUN mkdir -p /root/.ssh/

EXPOSE 22

CMD ["/usr/sbin/init"]