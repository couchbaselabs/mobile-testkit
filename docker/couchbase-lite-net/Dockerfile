FROM centos

MAINTAINER "Seth Rosetter" <seth.rosetter@gmail.com>

# Install git + .NET core deps
RUN yum update -y && \
    yum install -y git libunwind libicu

# Download and install .NET
RUN curl -sSL -o dotnet.tar.gz https://go.microsoft.com/fwlink/?linkid=848821 && \
    mkdir -p /opt/dotnet && \
    tar zxf dotnet.tar.gz -C /opt/dotnet
RUN ln -s /opt/dotnet/dotnet /usr/local/bin

WORKDIR /opt

# Git clone mobile-testkit
RUN git clone https://github.com/couchbaselabs/mobile-testkit.git
WORKDIR /opt/mobile-testkit/apps/testkit.net/

# Remove in PR
RUN git checkout feature/longevity-app

# Build the test app
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
RUN dotnet restore -s http://mobile.nuget.couchbase.com/nuget/Internal/ -s https://api.nuget.org/v3/index.json
RUN dotnet build

# Start the longevity test
WORKDIR /opt/mobile-testkit/apps/testkit.net/Testkit.Net.Core

CMD ["dotnet run"]