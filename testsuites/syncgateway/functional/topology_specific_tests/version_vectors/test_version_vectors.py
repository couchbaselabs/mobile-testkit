

from keywords import ClusterKeywords, couchbaseserver
from keywords.SyncGateway import (create_sync_gateways,
                                  sync_gateway_config_path_for_mode)
from keywords.utils import log_info
from testsuites.syncgateway.functional.topology_specific_tests.multiple_sync_gateways.test_sg_replicate import \
    create_sg_users_channels

bucket = "bucket-1"

def test_xdcr_2_cb_clusters_2_syncgateways(params_from_base_test_setup):
    cluster_config = params_from_base_test_setup["cluster_config"]
    config = sync_gateway_config_path_for_mode("sync_gateway_default",
                                               params_from_base_test_setup["mode"])

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=config
    )

    sg1_user, sg2_user = create_sg_users_channels(sg1, sg2, "db1", "db2")

    # Add docs to sg1 and sg2
    sg1_user.add_doc()
    sg2_user.add_doc()

    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    log_info("Topolofy {}".format(topology))
    cluster_servers = topology["couchbase_servers"]
    cb_server1 = couchbaseserver.CouchbaseServer(cluster_servers[0])
    cb_server2 = couchbaseserver.CouchbaseServer(cluster_servers[1])

    cb_server1.create_bucket(cluster_config, bucket)
    cb_server2.create_bucket(cluster_config, bucket)

    cb_server1.set_cross_cluster_versioning(bucket, True)
    cb_server2.set_cross_cluster_versioning("bucket-1", True)
