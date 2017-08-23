from keywords.couchbaseserver import CouchbaseServer, verify_server_version
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (verify_sg_accel_version,
                                  verify_sync_gateway_version,
                                  verify_sg_accel_product_info,
                                  verify_sync_gateway_product_info,
                                  SyncGateway)
from keywords.ClusterKeywords import ClusterKeywords
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords import document
from keywords import attachment


def test_upgrade(params_from_base_test_setup):
    # The initial versions of SG and CBS has already been provisioned at this point
    # We have to upgrade them to the upgraded versions
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    liteserv_storage_engine = params_from_base_test_setup["liteserv_storage_engine"]
    ls_url = params_from_base_test_setup["ls_url"]
    server_version = params_from_base_test_setup['server_version']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    sg_url = params_from_base_test_setup['sg_url']
    sg_admin_url = params_from_base_test_setup['sg_admin_url']
    sg_conf = "sync_gateway_default_functional_tests_{}".format(mode)

    # Add data to liteserv
    client = MobileRestClient()
    log_info("ls_url: {}".format(ls_url))
    ls_db = client.create_database(ls_url, name="ls_db")
    sg_db = "db"
    num_docs = 10

    # Create user and session on SG
    sg_user_channels = ["sg_user_channel"]
    sg_db = "db"
    sg_user_name = "sg_user"
    client.create_user(url=sg_admin_url, db=sg_db, name=sg_user_name, password="password", channels=sg_user_channels)
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)

    # Start continuous push pull replication ls_db_one <-> sg_db_one
    log_info("Starting replication from liteserv to sync gateway")
    repl_one = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db,
        to_url=sg_url, to_db=sg_db, to_auth=sg_session
    )
    client.wait_for_replication_status_idle(ls_url, repl_one)

    log_info("Starting replication from sync gateway to liteserv")
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_url, from_db=sg_db, from_auth=sg_session,
        to_db=ls_db
    )

    # Add docs to liteserv
    added_docs = client.add_docs(url=ls_url, db=ls_db, number=num_docs, id_prefix="ls_db_upgrade_doc", attachments_generator=attachment.generate_png_10_10)

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
    client.verify_docs_present(url=ls_url, db=ls_db, expected_docs=added_docs, attachments=True)
