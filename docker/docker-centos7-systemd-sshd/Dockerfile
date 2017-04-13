FROM alvaroaleman/centos7-systemd-sshd

# Update packages and install initscripts to workaround Couchbase Server installation
# issue where it expects /etc/init.d/functions to exist
RUN yum update -y systemd systemd-libs; yum install -y initscripts;

# Remove key added by parent layer
RUN rm -f /root/.ssh/authorized_keys