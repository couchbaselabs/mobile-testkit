
import pytest
import time

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import document
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.syncgateway
@pytest.mark.sanity
@pytest.mark.cachemanagement
def test_importDocs_withSharedBucketAccessFalse(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19Ai9SsMVrxc6JWVfcXc7y14JHtcYjPd5axBYyPQR0Dc/edit#gid=0
    Covers #1 and #3 of test cases link in excel sheet with xattrs enabled and disabled
    1. Start CBS and SGW with only enable_shared_bucket_access=false
    2. Create docs in CBS
    3. Verify docs are not imported to SGW as import_docs is set to false by default
    4. if Xattrs=true i.e if import_docs=true, Verify warn_count incremented on stats
    """

    sg_db = 'db'
    num_docs = 10
    bucket_name = 'data-bucket'
    sg_conf_name = "sync_gateway_with_shared_bucket_false"

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_client = MobileRestClient()

    cbs_host = host_for_url(cbs_url)

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    if sync_gateway_version < "2.7.0":
        pytest.skip('This functionality does not work for the versions below 2.7.0')

    expvars = sg_client.get_expvars(sg_admin_url)
    initial_warn_count = expvars["syncgateway"]["global"]["resource_utilization"]["warn_count"]

    # 1. Start CBS and SGW with only enable_shared_bucket_access=false
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    if cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    # 2. Create docs in CBS via SDK
    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs, channels=['shared'])
    log_info('Adding {} docs via SDK ...'.format(num_docs))
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    # 3. Verify docs are not imported to SGW as import_docs is set to false by default
    all_changes_total = sg_client.get_changes(url=sg_admin_url, db=sg_db, auth=None, since=0)
    assert len(all_changes_total["results"]) == 0

    # 4. if Xattrs=true i.e if import_docs=true, Verify warn_count incremented on stats
    if xattrs_enabled:
        expvars = sg_client.get_expvars(sg_admin_url)
        assert initial_warn_count < expvars["syncgateway"]["global"]["resource_utilization"]["warn_count"], "warn_count did not increment"


@pytest.mark.syncgateway
@pytest.mark.community
@pytest.mark.cachemanagement
def test_importDocs_defaultBehavior_withSharedBucketAccessTrue(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19Ai9SsMVrxc6JWVfcXc7y14JHtcYjPd5axBYyPQR0Dc/edit#gid=0
     Covers #2 of test cases link in excel sheet with xattrs enabled and disabled
    1. Start CBS and SGW with only enable_shared_bucket_access=True
    2. Create docs in CBS
    3. if it is CE :
        Verify docs are not imported as import_docs by default is false. Verify total _changes is 0
       if it is EE :
        Verify docs are imported as import_docs by default is true. Verify total _changes is number of docs created in CBS
    """

    sg_db = 'db'
    num_docs = 10
    bucket_name = 'data-bucket'
    sg_conf_name = "xattrs/no_import"

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    sg_ce = params_from_base_test_setup["sg_ce"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_client = MobileRestClient()

    cbs_host = host_for_url(cbs_url)

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))
    if sync_gateway_version < "2.7.0":
        pytest.skip('This functionality does not work for the versions below 2.7.0')

    # 1. Start CBS and SGW with only enable_shared_bucket_access=false
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    if cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    # 2. Create docs in CBS via SDK
    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs, channels=['shared'])
    log_info('Adding {} docs via SDK ...'.format(num_docs))
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)
    time.sleep(2)  # give some time to replicate to SGW

    # 3. Verify docs are not imported to SGW as import_docs is set to false by default
    all_changes_total = sg_client.get_changes(url=sg_admin_url, db=sg_db, auth=None, since=0)
    if sg_ce:
        assert len(all_changes_total["results"]) == 0
    else:
        assert len(all_changes_total["results"]) == num_docs


@pytest.mark.syncgateway
@pytest.mark.cachemanagement
def test_importPartitions_withSharedBucketAccessTrue(params_from_base_test_setup):
    """
    @summary :
    Test cases link on google drive : https://docs.google.com/spreadsheets/d/19Ai9SsMVrxc6JWVfcXc7y14JHtcYjPd5axBYyPQR0Dc/edit#gid=0
    Covers Test case #5 row #11
    1. Configure SGW with import_partitions >=1 , but less than 128
    2. Also configure enabled_shared_bucket_access=true
    3. Start SGW
    4. Create docs in CBS
    5. Verify import works from CBS to SGW
    """

    sg_db = 'db'
    num_docs = 10
    bucket_name = 'data-bucket'
    sg_conf_name = "sync_gateway_default_with_importpartitions"

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_client = MobileRestClient()

    cbs_host = host_for_url(cbs_url)

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))
    if sync_gateway_version < "2.7.0" or xattrs_enabled:
        pytest.skip('This functionality does not work for the versions below 2.7.0 , it does not need to run if xattrs enabled')

    # 1. Configure SGW with import_partitions >=1 , but less than 128
    # 2. Also configure enabled_shared_bucket_access=true
    # 3. Start SGW
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    if cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    # 4. Create docs in CBS via SDK
    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs, channels=['shared'])
    log_info('Adding {} docs via SDK ...'.format(num_docs))
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)
    time.sleep(1)  # give some time to import docs to SGW

    # 3. Verify docs are imported to SGW
    count = 0
    while count < 5:
        all_changes_total = sg_client.get_changes(url=sg_admin_url, db=sg_db, auth=None, since=0)
        assert len(all_changes_total["results"]) == num_docs
        if len(all_changes_total["results"]) == num_docs:
            break
        else:
            time.sleep(0.30)
            count = count + 1

    if count == 5:
        assert False, "did not import docs to sgw"
