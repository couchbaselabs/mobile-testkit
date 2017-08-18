from keywords.couchbaseserver import CouchbaseServer, verify_server_version
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (verify_sg_accel_version,
                                  verify_sync_gateway_version,
                                  verify_sg_accel_product_info,
                                  verify_sync_gateway_product_info,
                                  SyncGateway)

from keywords.ClusterKeywords import ClusterKeywords


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
    sg_conf = "sync_gateway_default_functional_tests_{}".format(mode)
    # TODO Add data to liteserv

    # Upgrade CBS
    cluster = Cluster(config=cluster_config)
    if len(cluster.servers) < 3:
        raise Exception("Please provide at least 3 servers")

    server_urls = []
    for server in cluster.servers:
        server_urls.append(server.url)

    primary_server = cluster.servers[0]
    secondary_server = cluster.servers[1]
    servers = cluster.servers[1:]

    log_info('------------------------------------------')
    log_info('START server cluster upgrade')
    log_info('------------------------------------------')
    # Upgrade all servers except the primary server
    for server in servers:
        log_info("Checking for the server version: {}".format(server_version))
        verify_server_version(server.host, server_version)
        log_info("Rebalance out server: {}".format(server.host))
        primary_server.rebalance_out(server_urls, server)
        log_info("Upgrading the server: {}".format(server.host))
        primary_server.upgrade_server(cluster_config, server_upgraded_version, target=server.host)
        log_info("Adding the node back to the cluster: {}".format(server.host))
        primary_server.add_node(server)
        log_info("Rebalance in server: {}".format(server.host))
        primary_server.rebalance_in(server_urls, server)
        log_info("Checking for the server version: {}".format(server_upgraded_version))
        verify_server_version(server.host, server_upgraded_version)

    # Upgrade the primary server
    primary_server_services = "kv,index,n1ql"
    log_info("Checking for the server version: {}".format(server_version))
    verify_server_version(primary_server.host, server_version)
    log_info("Rebalance out server: {}".format(primary_server.host))
    secondary_server.rebalance_out(server_urls, primary_server)
    log_info("Upgrading the server: {}".format(primary_server.host))
    secondary_server.upgrade_server(cluster_config, server_upgraded_version, target=primary_server.host)
    log_info("Adding the node back to the cluster: {}".format(primary_server.host))
    secondary_server.add_node(primary_server, services=primary_server_services)
    log_info("Rebalance in server: {}".format(primary_server.host))
    secondary_server.rebalance_in(server_urls, primary_server)
    log_info("Checking for the server version: {}".format(server_upgraded_version))
    verify_server_version(primary_server.host, server_upgraded_version)

    log_info("Upgraded all the server nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END server cluster upgrade')
    log_info('------------------------------------------')

    log_info('------------------------------------------')
    log_info('START Sync Gateway cluster upgrade')
    log_info('------------------------------------------')
    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
    sync_gateways = topology["sync_gateways"]
    for sg in sync_gateways:
        sg_ip = host_for_url(sg["admin"])
        sg_obj = SyncGateway()
        verify_sync_gateway_product_info(sg_ip)
        log_info("Checking for sunc gateway version: {}".format(sync_gateway_version))
        verify_sync_gateway_version(sg_ip, sync_gateway_version)
        log_info("Upgrading sync gateway: {}".format(sg_ip))
        sg_obj.upgrade_sync_gateways(cluster_config, sg_conf, sync_gateway_upgraded_version, sg_ip)
        verify_sync_gateway_product_info(sg_ip)
        log_info("Checking for sunc gateway version: {}".format(sync_gateway_upgraded_version))
        verify_sync_gateway_version(sg_ip, sync_gateway_upgraded_version)

    log_info("Upgraded all the sync gateway nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END Sync Gateway cluster upgrade')
    log_info('------------------------------------------')

    # TODO Verify data
