import pytest
import concurrent.futures

# from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import RBAC_FULL_ADMIN
from keywords.MobileRestClient import MobileRestClient
# from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import couchbaseserver
from keywords import document
from keywords import attachment
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from libraries.testkit.admin import Admin
from keywords.constants import RBAC_FULL_ADMIN
from requests.auth import HTTPBasicAuth
from libraries.testkit.data import Data
from testsuites.syncgateway.functional.tests.test_attachments import issue_request, verify_response_size
# from utilities.cluster_config_utils import is_ipv6

@pytest.mark.cloud
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_writing_attachment_to_couchbase_server(params_from_base_test_setup, sg_conf_name):
    """
    1. Start sync_gateway with sync function that rejects all writes:
    function(doc, oldDoc) {
      throw({forbidden:"No writes!"});
    }
    2. Create a doc with attachment
    3. Use CBS sdk to see if attachment doc exists.  Doc ID will look like _sync:att:sha1-Kq5sNclPz7QV2+lfQIuc6R7oRu0= (where the suffix is the digest)
    4. Assert att doc does not exist
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper = ClusterKeywords(cluster_config)
    cluster_helper.reset_cluster(cluster_config, sg_conf)
    cluster = Cluster(config=cluster_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_writing_attachment_to_couchbase_server'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_user_name = "sg_user"
    sg_user_password = "sg_user_password"

    sg_user_channels = ["NBC"]

    client = MobileRestClient()

    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    client.create_user(url=sg_url_admin, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels, auth=auth)
    sg_user_session = client.create_session(url=sg_url_admin, db=sg_db, name=sg_user_name, auth=auth)

    docs = client.add_docs(url=sg_url, db=sg_db, number=100, id_prefix=sg_db, channels=sg_user_channels, auth=sg_user_session)
    assert len(docs) == 100

    # Create doc with attachment and push to sync_gateway
    atts = attachment.load_from_data_dir(["sample_text.txt"])
    doc_with_att = document.create_doc(doc_id="att_doc", content={"sample_key": "sample_val"}, attachments=atts, channels=sg_user_channels)

    client.add_doc(url=sg_url, db=sg_db, doc=doc_with_att, auth=sg_user_session)
    server = couchbaseserver.CouchbaseServer(cbs_url)

    # Assert that the attachment doc gets written to couchbase server
    if sync_gateway_version >= "3.0.0":
        server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att2:", ipv6=cluster.ipv6)
    else:
        server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att:", ipv6=cluster.ipv6)
    num_att_docs = len(server_att_docs)
    assert num_att_docs == 1


@pytest.mark.cloud
@pytest.mark.parametrize("sg_conf_name, num_docs, accept_encoding, x_accept_part_encoding, user_agent, x509_cert_auth", [
    pytest.param("sync_gateway_gzip", 300, None, None, "CouchbaseLite/1.2", False, marks=[pytest.mark.oscertify, pytest.mark.sanity]),
])
def test_bulk_get_compression(params_from_base_test_setup, sg_conf_name, num_docs, accept_encoding,
                              x_accept_part_encoding, user_agent, x509_cert_auth):
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_bulk_get_compression'")
    log_info("Using cluster_config: {}".format(cluster_config))
    log_info("Using sg_conf: {}".format(sg_conf))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using user_agent: {}".format(user_agent))
    log_info("Using accept_encoding: {}".format(accept_encoding))
    log_info("Using x_accept_part_encoding: {}".format(x_accept_part_encoding))

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_config = temp_cluster_config
    cluster = Cluster(config=cluster_config)
    # cluster.reset(sg_config_path=sg_conf)

    admin = Admin(cluster.sync_gateways[0])
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    if auth:
        admin.auth = HTTPBasicAuth(auth[0], auth[1])

    user = admin.register_user(cluster.sync_gateways[0], "db", "seth", "password", channels=["seth"])

    doc_body = Data.load("mock_users_20k.json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=libraries.testkit.settings.MAX_REQUEST_WORKERS) as executor:
        futures = [executor.submit(user.add_doc, doc_id="test-{}".format(i), content=doc_body) for i in range(num_docs)]
        for future in concurrent.futures.as_completed(futures):
            try:
                log_info(future.result())
            except Exception as e:
                log_info("Failed to push doc: {}".format(e))

    docs = [{"id": "test-{}".format(i)} for i in range(num_docs)]
    payload = {"docs": docs}

    # Issue curl request and get size of request
    response_size = issue_request(cluster.sync_gateways[0], user_agent, accept_encoding, x_accept_part_encoding, payload)
    log_info("Response size: {}".format(response_size))

    # Verfiy size matches expected size
    verify_response_size(user_agent, accept_encoding, x_accept_part_encoding, response_size)