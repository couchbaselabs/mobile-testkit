
FROM williamyeh/ansible:centos7

# Update Yum and install epel
RUN yum update -y && \
    yum install -y epel-release && \
    yum groupinstall -y development

# Install dependencies
RUN yum install -y \
  git \
  libev \
  libevent \
  python-devel \
  python-pip \
  unzip \
  wget

# Install couchbase C SDK
RUN cd /tmp/ && \
    wget http://packages.couchbase.com/clients/c/libcouchbase-2.5.6_centos7_x86_64.tar && \
    tar xvf libcouchbase-2.5.6_centos7_x86_64.tar && \
    cd libcouchbase-2.5.6_centos7_x86_64 && \
    rpm -ivh libcouchbase-devel-2.5.6-1.el7.centos.x86_64.rpm \
             libcouchbase2-core-2.5.6-1.el7.centos.x86_64.rpm \
	     libcouchbase2-bin-2.5.6-1.el7.centos.x86_64.rpm \
	     libcouchbase2-libevent-2.5.6-1.el7.centos.x86_64.rpm && \
    rm -f *.rpm	     
    
# Install pip packages
RUN pip install troposphere && \
    pip install awscli && \
    pip install boto && \
    pip install pytest && \
    pip install futures && \
    pip install requests



