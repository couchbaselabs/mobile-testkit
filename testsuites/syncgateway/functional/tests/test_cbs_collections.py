import pytest

from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import couchbaseserver
from keywords import document
from libraries.testkit.cluster import Cluster
from keywords.utils import host_for_url, log_info
from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import wait_until_docs_imported_from_server
from keywords.couchbaseserver import get_server_version
from utilities.cluster_config_utils import get_cluster
from utilities.cluster_config_utils import load_cluster_config_json
from keywords.constants import RBAC_FULL_ADMIN


@pytest.mark.syncgateway
@pytest.mark.collections
def test_userdefind_collections(params_from_base_test_setup):
    """
    @summary
    https://docs.google.com/spreadsheets/d/1TZd0YrDh2lMJldNCst-bR53eE8vok8wWoo1wCHdGDEU/edit#gid=0
    row #9
    "1. Create docs via sdk with and without attachments on default collections
     2. Create docs via sdk using user defined collections
     3. Verify docs created in default collections are imported to SGW
     4. Verify docs created in user defined collections will not get imported to SGW"
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    sg_conf_name = 'sync_gateway_default_functional_tests'
    mode = "cc"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_helper.reset_cluster(cluster_config, sg_conf)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    cbs_url = topology["couchbase_servers"][0]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_client = MobileRestClient()
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    cbs_ip = host_for_url(cbs_url)
    sg_db = "db"
    bucket = "data-bucket"
    channels = ["ABC"]
    num_sdk_docs = 10

    server_version = get_server_version(cbs_ip, cbs_ssl=ssl_enabled)
    if not xattrs_enabled or server_version < "7.0.0":
        pytest.skip('This test require --xattrs flag or server version 7.0 and up')
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_conf)
    if sg_platform == "windows" or "macos" in sg_platform:
        json_cluster = load_cluster_config_json(cluster_config)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(cluster.servers[0].host)

    # 1. Create docs via sdk with and without attachments on default collections
    if ssl_enabled and cluster.ipv6:
        connection_url = "couchbases://{}?ssl=no_verify&ipv6=allow".format(cbs_ip)
    elif ssl_enabled and not cluster.ipv6:
        connection_url = "couchbases://{}?ssl=no_verify".format(cbs_ip)
    elif not ssl_enabled and cluster.ipv6:
        connection_url = "couchbase://{}?ipv6=allow".format(cbs_ip)
    else:
        connection_url = "couchbase://{}".format(cbs_ip)
    sdk_client = get_cluster(connection_url, bucket)
    sdk_doc_bodies = document.create_docs('sdk_default', number=num_sdk_docs, channels=channels)
    print("sdk doc bodies are ", sdk_doc_bodies)
    sdk_docs = {doc['uni_key_id']: doc for doc in sdk_doc_bodies}

    sdk_client.upsert_multi(sdk_docs)

    # 2. Create docs via sdk using user defined collections
    scope = cb_server.create_scope(bucket)
    collection = cb_server.create_collection(bucket, scope)
    collection_id = cb_server.get_collection_id(bucket, scope, collection)
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_expvars = sg_client.get_expvars(sg_admin_url, auth=auth)
    import_count = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    remote_executor.execute("/opt/couchbase/bin/cbworkloadgen -n localhost:8091 -i {} -b {} -j -c 0x{} -u Administrator -p password".format(num_sdk_docs, bucket, collection_id))
    wait_until_docs_imported_from_server(sg_admin_url, sg_client, sg_db, num_sdk_docs, import_count, auth=auth)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, auth=auth)["rows"]
    assert sum("sdk_default" in s["id"] for s in sg_docs) == num_sdk_docs, "default collections docs are not imported to sync gateway"
    assert sum("pymc" in s for s in sg_docs) == 0, "user defined docs are imported to sync gateway"
