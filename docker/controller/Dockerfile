
FROM williamyeh/ansible:centos7

# Update Yum and install epel
RUN yum update -y && yum install -y \
  epel-release 

# Install dependencies
RUN yum install -y \
  git \
  python-pip \
  unzip

# Install pip packages
RUN pip install troposphere && \
    pip install awscli && \
    pip install boto && \
    pip install pytest && \
    pip install futures && \
    pip install requests



