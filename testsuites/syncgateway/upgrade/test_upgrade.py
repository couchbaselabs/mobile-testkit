from keywords.couchbaseserver import CouchbaseServer, verify_server_version
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
    server_version = params_from_base_test_setup['server_version']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']

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
        verify_server_version(server.host, server_version)
        log_info("Rebalance out server: {}".format(server.host))
        primary_server.rebalance_out(server_urls, server)
        log_info("Upgrading the server: {}".format(server.host))
        primary_server.upgrade_server(cluster_config, server_upgraded_version, target=server.host)
        log_info("Adding the node back to the cluster: {}".format(server.host))
        primary_server.add_node(server)
        log_info("Rebalance in server: {}".format(server.host))
        primary_server.rebalance_in(server_urls, server)
        verify_server_version(server.host, server_upgraded_version)

    # Upgrade the primary server
    verify_server_version(primary_server.host, server_version)
    log_info("Rebalance out server: {}".format(primary_server.host))
    secondary_server.rebalance_out(server_urls, primary_server)
    log_info("Upgrading the server: {}".format(primary_server.host))
    secondary_server.upgrade_server(cluster_config, server_upgraded_version, target=primary_server.host)
    log_info("Adding the node back to the cluster: {}".format(primary_server.host))
    secondary_server.add_node(primary_server)
    log_info("Rebalance in server: {}".format(primary_server.host))
    secondary_server.rebalance_in(server_urls, primary_server)
    verify_server_version(primary_server.host, server_upgraded_version)

    log_info("Upgraded all the server nodes in the cluster")

    # TODO Upgrade SG

    # TODO Verify data
