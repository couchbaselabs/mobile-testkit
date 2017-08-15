from couchbaseserver import CouchbaseServer
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
    cluster = Cluster(config=cluster_config)
    log_info("cluster.servers: {}".format(cluster.servers))

    # TODO Upgrade SG

    # TODO Verify data
