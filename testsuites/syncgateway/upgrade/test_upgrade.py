import time

from keywords.couchbaseserver import CouchbaseServer
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info


def test_upgrade(params_from_base_test_setup):
    # The initial versions of SG and CBS has already been provisioned at this point
    # We have to upgrade them to the upgraded versions
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]

    # TODO Add data to liteserv

    # Upgrade CBS
    cluster = Cluster(config=cluster_config)
    if len(cluster.servers) < 3:
        raise Exception("Please provide at least 3 servers")

    primary_server = cluster.servers[0]
    secondary_server = cluster.servers[1]
    servers = cluster.servers[1:]
    server_urls = []
    for server in cluster.servers:
        server_urls.append(server.url)

    # Upgrade all servers except the primary server
    for server in servers:
        log_info("Rebalance out server: {}".format(server.host))
        primary_server.rebalance_out(server_urls, server)
        log_info("Upgrade the server: {}".format(server.host))
        time.sleep(10)
        log_info("Rebalance in server: {}".format(server.host))
        primary_server.rebalance_in(server_urls, server)

    # Upgrade the primary server
    # log_info("Rebalance out server: {}".format(primary_server.host))
    # secondary_server.rebalance_out(server_urls, primary_server)
    # log_info("Upgrade the server: {}".format(primary_server.host))
    # log_info("Rebalance in server: {}".format(primary_server.host))
    # secondary_server.rebalance_in(server_urls, primary_server)
    
    
    # TODO Upgrade SG

    # TODO Verify data
