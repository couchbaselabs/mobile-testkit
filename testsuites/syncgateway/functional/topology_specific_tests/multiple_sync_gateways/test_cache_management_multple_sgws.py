import pytest
import time

from keywords.constants import RBAC_FULL_ADMIN
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode, create_docs_via_sdk
from keywords import document
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit import cluster
from concurrent.futures import ThreadPoolExecutor
from libraries.testkit.prometheus import verify_stat_on_prometheus
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config


@pytest.mark.syncgateway
@pytest.mark.topospecific
@pytest.mark.oscertify
@pytest.mark.sanity
def test_importdocs_false_shared_bucket_access_true(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19Ai9SsMVrxc6JWVfcXc7y14JHtcYjPd5axBYyPQR0Dc/edit#gid=0
    1. Enable shared_bucket_access = true on all nodes
    2. Have 2 SGWs and have CBS set up  with above configuation on SGW.
    3. Have one node as import_docs=false
    4. Create docs in CBs
    5. Verify  SGW node which does not have config import_docs=false has docs imported.
    6. Verify import_count on SG1 should show 0
    7. Verify import_count on SGW2 should show the number matches with num of docs

    """

    sg_db = 'db'
    num_docs = 10
    bucket_name = 'data-bucket'
    sg_conf_name1 = "import_false"
    sg_conf_name2 = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_conf1 = sync_gateway_config_path_for_mode(sg_conf_name1, mode)
    sg_conf2 = sync_gateway_config_path_for_mode(sg_conf_name2, mode)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None

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
    cbs_cluster.reset(sg_config_path=sg_conf1)
    sg1 = cbs_cluster.sync_gateways[0]
    sg2 = cbs_cluster.sync_gateways[1]
    status = sg1.restart(config=sg_conf1, cluster_config=cluster_conf)
    assert status == 0, "Sync_gateway1  did not start"
    status = sg2.restart(config=sg_conf2, cluster_config=cluster_conf)
    assert status == 0, "Sync_gateway2  did not start"

    if cbs_cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')

    # 4. Create docs in CBs
    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs, channels=['shared'], non_sgw=True)
    log_info('Adding {} docs via SDK ...'.format(num_docs))
    sdk_docs = {doc['id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)
    time.sleep(3)
    # 5. Verify  SGW node which does not have config import_docs=false has docs imported.
    # but not for the other SGW node.
    sg_client.get_changes(url=sg1.admin.admin_url, db=sg_db, auth=auth, since=0)
    sg_client.get_changes(url=sg2.admin.admin_url, db=sg_db, auth=auth, since=0)
    sg1_expvars = sg_client.get_expvars(sg1.admin.admin_url, auth=auth)
    sg2_expvars = sg_client.get_expvars(sg2.admin.admin_url, auth=auth)

    # 6. Verify import_count on SG1 should show 0
    is_import_count_available = 0
    try:
        sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    except KeyError:
        is_import_count_available = 1
    assert is_import_count_available == 1 or sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"] == 0, "import_count appears on sync gateway node"

    # 7. Verify import_count on SGW2 should show the number matches with num of docs
    sg2_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    assert sg2_import_count == num_docs, "import count should be equal to number of docs"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.community
def test_sgw_cache_management_multiple_sgws(params_from_base_test_setup):
    """
    @summary :
    1.Have 3 SGWs( no load balancer required)  with shared_bucket_access=true and have CBS set up
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    disable_persistent_config = params_from_base_test_setup["disable_persistent_config"]

    if sg_ce:
        if not xattrs_enabled:
            pytest.skip('XATTR tests require --xattrs flag')
        sg_conf_name = "sync_gateway_default_functional_tests"
    else:
        sg_conf_name = "xattrs/no_import"

    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None

    # 1. Have 2 SGWs  with shared_bucket_access=true and have CBS set up
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cluster_utils.reset_cluster(cluster_config=cluster_config, sync_gateway_config=sg_conf_path)

    sg_db = "db"
    num_docs = 100
    # bucket_name = 'data-bucket'
    buckets = get_buckets_from_sync_gateway_config(sg_conf_path, cluster_config)
    bucket_name = buckets[0]

    client = MobileRestClient()
    c = cluster.Cluster(config=cluster_config)
    sg1 = c.sync_gateways[0]
    sg2 = c.sync_gateways[1]
    sg3 = c.sync_gateways[2]
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_cluster = Cluster(config=cluster_config)

    # 2. Create docs in CBS
    create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, num_docs)
    time.sleep(15)  # needed as windows take more time to import

    # 3.Verify following stats
    #    EE - import_cancel_cas =0
    #       - import_count = num of docs
    #    CE - import_cancel_cas  is not equal to 0
    #    import_count + import_cancel_cas = num_docs
    sg1_expvars = client.get_expvars(sg1.admin.admin_url, auth=auth)
    sg2_expvars = client.get_expvars(sg2.admin.admin_url, auth=auth)
    sg3_expvars = client.get_expvars(sg3.admin.admin_url, auth=auth)
    if sg_ce:
        log_info("Verify import_cancel_cas is not 0 and import_count + import_cancel_cas = num_docs")
        sg1_cancel_cas = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg2_cancel_cas = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
        sg2_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        # sg3_cancel_cas = sg3_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
        sg3_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        assert sg1_import_count + sg1_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg1 node"
        assert sg2_import_count + sg2_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg2 node"
        # assert sg3_import_count + sg3_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg3 node"
    else:
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg2_import_count = sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg3_import_count = sg3_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        if disable_persistent_config:
            assert sg1_import_count + sg2_import_count + sg3_import_count == num_docs, "Not all docs imported"
        else:
            assert sg1_import_count + sg2_import_count + sg3_import_count <= num_docs, "Not all docs imported"
        assert sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"] == 0, "import cancel cas is not zero on sgw node 1"
        assert sg2_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"] == 0, "import cancel cas is not zero on sgw node 2"
        assert sg3_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"] == 0, "import cancel cas is not zero on sgw node 3"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.community
def test_sgw_high_availability(params_from_base_test_setup, setup_basic_sg_conf):
    """
    @summary :
    1. Start 2 sgw nodes
    2. Start a thread to write docs via SDK
    3. Bring down 1 sgw node in main thread
    4. Wait for 20 secs in thread 1
    5. Stop writing docs in couchbaase server in thread 1
    6. Validate all docs written on CBS is imported to SGW
    7. Verify stats
        EE - import_cancel_cas =0
           - import_count = num of docs
        CE - import_cancel_cas  is not equal to 0
        import_count + import_cancel_cas = num_docs
    """

    cluster_config = setup_basic_sg_conf["cluster_config"]
    cbs_cluster = setup_basic_sg_conf["cbs_cluster"]
    sg2 = setup_basic_sg_conf["sg2"]
    sg_ce = params_from_base_test_setup["sg_ce"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    sg_conf = setup_basic_sg_conf["sg_conf"]
    sg_db = "db"
    sg2.restart(config=sg_conf, cluster_config=cluster_config)
    sg_client = MobileRestClient()
    prometheus_enabled = params_from_base_test_setup["prometheus_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    if not xattrs_enabled:
        pytest.skip(' This test require --xattrs flag')

    # 1. Start 2 sgw nodes
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cluster_utils.reset_cluster(cluster_config=cluster_config, sync_gateway_config=sg_conf)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None

    num_docs = 100
    # bucket_name = 'data-bucket'
    buckets = get_buckets_from_sync_gateway_config(sg_conf, cluster_config)
    bucket_name = buckets[0]

    sg1 = cbs_cluster.sync_gateways[0]
    sg3 = cbs_cluster.sync_gateways[2]
    cbs_url = cluster_topology['couchbase_servers'][0]

    # 2. Start a thread to write docs via SDK
    with ThreadPoolExecutor(max_workers=4) as tpe:
        cbs_docs_via_sdk = tpe.submit(create_doc_via_sdk_individually, cbs_url, cbs_cluster, bucket_name, num_docs)
        # 3. Bring down 1 sgw node in main thread
        sg2.stop()
        sg_docs = sg_client.get_all_docs(url=sg1.admin.admin_url, db=sg_db, auth=auth)["rows"]
        sg3_docs = sg_client.get_all_docs(url=sg3.admin.admin_url, db=sg_db, auth=auth)["rows"]
        diff_docs = num_docs - (len(sg_docs) + len(sg3_docs))
        # diff_docs = num_docs - len(sg_docs)
        cbs_docs_via_sdk.result()

    retries = 0
    while retries < 10:
        sg_docs = sg_client.get_all_docs(url=sg1.admin.admin_url, db=sg_db, auth=auth)["rows"]
        if len(sg_docs) == num_docs:
            break
        retries = retries + 1
        time.sleep(2)
    assert len(sg_docs) == num_docs, "not all docs imported from server"
    sg1_expvars = sg_client.get_expvars(sg1.admin.admin_url, auth=auth)
    sg3_expvars = sg_client.get_expvars(sg3.admin.admin_url, auth=auth)
    sg1_cancel_cas = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_cancel_cas"]
    if sg_ce:
        log_info("Verify import_cancel_cas is not 0 and import_count + import_cancel_cas = num_docs")
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        assert sg1_import_count + sg1_cancel_cas == num_docs, "import count and cancel cas did not match to num of docs on sg1 node"
        assert sg1_cancel_cas is not 0, "cancel_ca value is 0 on CE"
    else:
        assert sg1_cancel_cas == 0, "cancel_ca value is not 0 on EE"
        sg1_import_count = sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg3_import_count = sg3_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        sg1_sg3_import_count = sg1_import_count + sg3_import_count
        assert sg1_sg3_import_count > diff_docs, "Not all docs imported"
        if prometheus_enabled and sync_gateway_version >= "2.8.0":
            assert verify_stat_on_prometheus("sgw_shared_bucket_import_import_count") == sg1_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]


def create_doc_via_sdk_individually(cbs_url, cbs_cluster, bucket_name, num_docs):
    for i in range(0, num_docs):
        doc_name = 'sdk_{}'.format(i)
        create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, 1, doc_name=doc_name)


@pytest.fixture(scope="function")
def setup_basic_sg_conf(params_from_base_test_setup):
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cbs_cluster = cluster.Cluster(cluster_config)
    sg2 = cbs_cluster.sync_gateways[1]

    yield{
        "cbs_cluster": cbs_cluster,
        "sg2": sg2,
        "mode": mode,
        "cluster_config": cluster_config,
        "sg_conf": sg_conf
    }
