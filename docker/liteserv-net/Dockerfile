FROM mono

# Install deps
RUN apt-get update && \ 
    apt-get -y install wget zip unzip

# Download / unzip LiteServ
RUN wget http://latestbuilds.hq.couchbase.com/couchbase-lite-net/1.4.0/4/LiteServ.zip && \
    unzip LiteServ.zip -d LiteServ

# Run LiteServ
EXPOSE 59840
CMD ["mono", "LiteServ/LiteServ.exe"]