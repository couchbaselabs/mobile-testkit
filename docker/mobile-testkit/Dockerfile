FROM centos:7

# Update Yum and install epel
RUN yum update -y && \
    yum install -y epel-release && \
    yum groupinstall -y development

# Install dependencies
RUN yum install -y \
    git \
    libevent \
    openssl-devel \
    unzip \
    wget

# Install prerequisites for the Couchbase Server python SDK
# https://developer.couchbase.com/documentation/server/current/sdk/python/start-using-sdk.html
RUN wget http://packages.couchbase.com/releases/couchbase-release/couchbase-release-1.0-2-x86_64.rpm; \
    rpm -iv couchbase-release-1.0-2-x86_64.rpm; \
    yum install -y \
        libcouchbase-devel \
        gcc \
        gcc-c++ \
        python-devel \
        python-pip

RUN pip install --upgrade pip

WORKDIR /opt

# Git clone mobile-testkit
RUN git clone https://github.com/couchbaselabs/mobile-testkit.git

WORKDIR /opt/mobile-testkit

# Install dependencies
RUN pip install -r requirements.txt

# Create ansible config for sample
RUN cp ansible.cfg.example ansible.cfg

# Set the correct default user
RUN sed -i 's/remote_user = vagrant/remote_user = root/' ansible.cfg

# Create .ssh directory for key installation
RUN mkdir -p /root/.ssh

# set python env
ENV PYTHONPATH=/opt
ENV ANSIBLE_CONFIG=/opt/ansible.cfg

# Remove later, working on end to end automation
CMD ["/bin/bash"]
