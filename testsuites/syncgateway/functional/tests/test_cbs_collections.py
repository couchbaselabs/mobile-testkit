import pytest

from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import couchbaseserver
from keywords import document
from keywords import attachment
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import is_ipv6
from keywords.utils import host_for_url, log_info
from couchbase.bucket import Bucket
from keywords.constants import SDK_TIMEOUT
from keywords.remoteexecutor import RemoteExecutor

@pytest.mark.syncgateway
@pytest.mark.collections
def test_userdefind_collections(params_from_base_test_setup):
    """
    "1. Create docs via sdk with and without attachments on default collections
     2. Create docs via sdk using user defined collections
     3. Verify docs created in default collections are imported to SGW
     4. Verify docs created in user defined collections will not get imported to SGW
     5. Verify. nothing breaks and SGW works "
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_conf_name = 'sync_gateway_default_functional_tests'
    mode = "cc"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_helper.reset_cluster(cluster_config, sg_conf)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_client = MobileRestClient()
    sync_gateway = SyncGateway()
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    cbs_ip = host_for_url(cbs_url)
    sg_db = "db"
    bucket = "data-bucket"
    sg_user = "sg_user"
    sg_password = "password"
    channels = ["ABC"]
    num_sdk_docs = 10

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_conf)
    # sg_client.create_user(url=sg_admin_url, db=sg_db, name=sg_user, password=sg_password, channels=channels)
    # session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=sg_user)
    remote_executor = RemoteExecutor(cluster.servers[0].ip)

    # 1. Create docs via sdk with and without attachments on default collections
    if ssl_enabled and cluster.ipv6:
        connection_url = "couchbases://{}/{}?ssl=no_verify&ipv6=allow".format(cbs_ip, bucket)
    elif ssl_enabled and not cluster.ipv6:
        connection_url = "couchbases://{}/{}?ssl=no_verify".format(cbs_ip, bucket)
    elif not ssl_enabled and cluster.ipv6:
        connection_url = "couchbase://{}/{}?ipv6=allow".format(cbs_ip, bucket)
    else:
        connection_url = 'couchbase://{}/{}'.format(cbs_ip, bucket)
    sdk_client = Bucket(connection_url, password='password', timeout=SDK_TIMEOUT)
    sdk_doc_bodies = document.create_docs('sdk_default', number=num_sdk_docs, channels=channels)
    sdk_doc_ids = [doc['_id'] for doc in sdk_doc_bodies]
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)

    # 2. Create docs via sdk using user defined collections
    # scope = cb_server.create_scope(bucket)
    # collection = cb_server.create_collection(bucket, scope)
    # doc_id = "u-defined-collection1"
    # doc_body = document.create_doc(doc_id=doc_id, channels=channels)
    # doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=session)
    # print("doc from sg_client ", doc)
    remote_executor.execute("/opt/couchbase/bin/cbworkloadgen -n 10.112.194.101:8091 -i 100 -b testBucket -j -c 0x8 -u Administrator -p password")
    # cb_server.create_doc_with_user_defined_collection(connection_url, bucket, scope, collection, doc_id, doc)
