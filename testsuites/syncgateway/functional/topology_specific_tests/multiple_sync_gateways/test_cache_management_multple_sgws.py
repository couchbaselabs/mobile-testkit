import pytest
import time

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import document
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit import cluster
from testsuites.syncgateway.sgw_utilities import create_docs_via_sdk


@pytest.mark.syncgateway
def test_importdocs_false_shared_bucket_access_true(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19Ai9SsMVrxc6JWVfcXc7y14JHtcYjPd5axBYyPQR0Dc/edit#gid=0
    1. Enable shared_bucket_access = true on all nodes
    2. Have 2 SGWs and have CBS set up  with above configuation on SGW.
    3. Have one node as import_docs=false
    4. Create docs in CBs
    5. Verify  SGW node which does not have config import_docs=false has docs imported.
        but not for the other SGW node.
    """

    sg_db = 'db'
    num_docs = 10
    bucket_name = 'data-bucket'
    sg_conf_name1 = "import_false"
    sg_conf_name2 = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    sg_conf1 = sync_gateway_config_path_for_mode(sg_conf_name1, mode)
    sg_conf2 = sync_gateway_config_path_for_mode(sg_conf_name2, mode)

    sg_client = MobileRestClient()
    cluster_utils = ClusterKeywords(cluster_conf)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_conf)
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_host = host_for_url(cbs_url)
    cbs_cluster = Cluster(config=cluster_conf)

    if xattrs_enabled:
        pytest.skip('Do not need to run with xattrs enabled')

    log_info('sg_conf1: {}'.format(sg_conf1))
    log_info('sg_conf2: {}'.format(sg_conf2))

    # 1. Enable shared_bucket_access = true on all nodes
    # 2. Have 2 SGWs and have CBS set up  with above configuation on SGW.
    # 3. Have one node as import_docs=false
    c = cluster.Cluster(config=cluster_conf)
    sg1 = c.sync_gateways[0]
    sg2 = c.sync_gateways[1]
    status = sg1.restart(config=sg_conf1, cluster_config=cluster_conf)
    assert status == 0, "Sync_gateway1  did not start"
    status = sg2.restart(config=sg_conf2, cluster_config=cluster_conf)
    assert status == 0, "Sync_gateway2  did not start"

    if cbs_cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    # 4. Create docs in CBs
    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs, channels=['shared'])
    log_info('Adding {} docs via SDK ...'.format(num_docs))
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    # 5. Verify  SGW node which does not have config import_docs=false has docs imported.
    #  but not for the other SGW node.
    sg1_changes = sg_client.get_changes(url=sg1.admin.admin_url, db=sg_db, auth=None, since=0)
    assert len(sg1_changes["results"]) == 0

    sg2_changes = sg_client.get_changes(url=sg2.admin.admin_url, db=sg_db, auth=None, since=0)
    assert len(sg2_changes["results"]) == num_docs


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.community
def test_sgw_cache_management_multiple_sgws(params_from_base_test_setup):
    """
    @summary :
    1.Have 2 SGWs( no load balancer required)  with shared_bucket_access=true and have CBS set up
    2. Create docs in CBS
    3.Verify following stats
        EE - import_cancel_cas =0
           - import_count = num of docs
        CE - import_cancel_cas  is not equal to 0
        import_count + import_cancel_cas = num_docs
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_ce = params_from_base_test_setup["sg_ce"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    if sg_ce:
        if not xattrs_enabled:
            pytest.skip('XATTR tests require --xattrs flag')
        sg_conf_name = "sync_gateway_default_functional_tests"
    else:
        sg_conf_name = "xattrs/no_import"

    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 1. Have 2 SGWs  with shared_bucket_access=true and have CBS set up
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cluster_utils.reset_cluster(cluster_config=cluster_config, sync_gateway_config=sg_conf_path)

    sg_db = "db"
    num_docs = 100
    bucket_name = 'data-bucket'

    client = MobileRestClient()
    c = cluster.Cluster(config=cluster_config)
    sg1 = c.sync_gateways[0]
    sg2 = c.sync_gateways[1]
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_cluster = Cluster(config=cluster_config)

    # 2. Create docs in CBS
    create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, num_docs)
    time.sleep(3)

    # 3.Verify following stats
    #    EE - import_cancel_cas =0
    #       - import_count = num of docs
    #    CE - import_cancel_cas  is not equal to 0
    #    import_count + import_cancel_cas = num_docs
    sg1_expvars = client.get_expvars(sg1.admin.admin_url)
    sg2_expvars = client.get_expvars(sg2.admin.admin_url)
    if sg_ce:
        log_info("Verify import_cancel_cas is not 0 and import_count + import_cancel_cas = num_docs")
        sg1_cancel_cas = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg2_cancel_cas = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
        sg2_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        assert sg1_import_count + sg1_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg1 node"
        assert sg2_import_count + sg2_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg2 node"
    else:
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg2_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        assert sg1_import_count + sg2_import_count == num_docs, "Not all docs imported"
        assert sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"] == 0, "import cancel cas is not zero on sgw node 1"
        assert sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"] == 0, "import cancel cas is not zero on sgw node 2"
