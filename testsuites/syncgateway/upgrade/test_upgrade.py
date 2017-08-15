from keywords.couchbaseserver import CouchbaseServer
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info


def test_system_test(params_from_base_test_setup):
    # The initial versions of SG and CBS has already been provisioned at this point
    # We have to upgrade them to the upgraded versions
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    liteserv_host = params_from_base_test_setup["liteserv_host"]
    liteserv_port = params_from_base_test_setup["liteserv_port"]

    # TODO Add data to liteserv

    # Upgrade CBS
    admin_server_url = None
    server_urls = []
    cluster = Cluster(config=cluster_config)
    for server in cluster.servers:
        server_urls.append(server.url)

    admin_server_url = server_urls.remove(0)

    for server in cluster.servers:
        if admin_server_url == server.host:
            temp_admin_server = 
        log_info("Rebalance out server: {}".format(server.host))
        log_info("Admin server: {}".format(admin_server_url))
        # server.rebalance_out(server_urls, server)
        log_info("Upgrade the server: {}".format(server.host))
        log_info("Rebalance in server: {}".format(server.host))
        # server.rebalance_in(server_urls, server)

    log_info("server_urls: {}".format(server_urls))
    # TODO Upgrade SG

    # TODO Verify data
