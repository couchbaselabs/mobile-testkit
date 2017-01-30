import pytest

from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import couchbaseserver
from keywords import document


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_attachment_revpos_when_ancestor_unavailable(params_from_base_test_setup, sg_conf_name):
    """
    Creates a document with an attachment, then updates that document so that
    the body of the revision that originally pushed the document is no
    longer available.  Add a new revision that's not a child of the
    active revision, and validate that it's uploaded successfully.
    Example:
       1. Document is created with attachment at rev-1
       2. Document is updated (strip digests and length, only put revpos & stub) multiple times on the server, goes to rev-4
       3. Client attempts to add a new (conflicting) revision 2, with parent rev-1.
       4. If the body of rev-1 is no longer available on the server (temporary backup of revision has expired, and is no longer stored
         in the in-memory rev cache), we were throwing an error to client
         because we couldn't verify based on the _attachments property in rev-1.
       5. In this scenario, before returning error, we are now checking if the active revision has a common ancestor with the incoming revision.
    If so, we can validate any revpos values equal to or earlier than the common ancestor against the active revision
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper = ClusterKeywords()
    cluster_helper.reset_cluster(cluster_config, sg_conf)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    channels_list = ["ABC"]

    client = MobileRestClient()
    sg_util = SyncGateway()
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)

    user1 = client.create_user(url=sg_url_admin, db=sg_db, name="user1", password="password", channels=channels_list)
    doc_with_att = document.create_doc(doc_id="att_doc", content={"sample_key": "sample_val"}, attachment_name="sample_text.txt", channels=channels_list)

    doc_gen_1 = client.add_doc(url=sg_url, db=sg_db, doc=doc_with_att, auth=user1)
    client.update_doc(url=sg_url, db=sg_db, doc_id=doc_gen_1["id"], number_updates=10, auth=user1)

    # Clear cached rev doc bodys from server and cycle sync_gateway
    sg_util.stop_sync_gateway(cluster_config=cluster_config, url=sg_url)

    cb_server.delete_couchbase_server_cached_rev_bodies(bucket=bucket)
    sg_util.start_sync_gateway(cluster_config=cluster_config, url=sg_url, config=sg_conf)

    client.add_conflict(
        url=sg_url, db=sg_db,
        doc_id=doc_gen_1["id"],
        parent_revisions=doc_gen_1["rev"],
        new_revision="2-foo",
        auth=user1
    )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_attachment_revpos_when_ancestor_unavailable_active_revision_doesnt_share_ancestor(params_from_base_test_setup, sg_conf_name):
    """
    Creates a document with an attachment, then updates that document so that
    the body of the revision that originally pushed the document is no
    longer available.  Add a new revision that's not a child of the
    active revision, and validate that it's uploaded successfully.
    Example:
       1. Document is created with no attachment at rev-1
       2. Server adds revision with attachment at rev-2 {"hello.txt", revpos=2}
       2. Document is updated multiple times on the server, goes to rev-4
       3. Client attempts to add a new (conflicting) revision 3a, with ancestors rev-2a (with it's own attachment), rev-1.
       4. When client attempts to push rev-3a with attachment stub {"hello.txt", revpos=2}.  Should throw an error, since the revpos
       of the attachment is later than the common ancestor (rev-1)
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper = ClusterKeywords()
    cluster_helper.reset_cluster(cluster_config, sg_conf)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable_active_revision_doesnt_share_ancestor'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_user_name = "sg_user"
    sg_user_password = "password"

    sg_user_channels = ["NBC"]

    client = MobileRestClient()

    client.create_user(url=sg_url_admin, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels)
    sg_user_session = client.create_session(url=sg_url_admin, db=sg_db, name=sg_user_name)

    doc = document.create_doc(doc_id="doc_1", content={"sample_key": "sample_val"}, channels=sg_user_channels)
    doc_gen_1 = client.add_doc(url=sg_url, db=sg_db, doc=doc, auth=sg_user_session)
    client.update_doc(url=sg_url, db=sg_db, doc_id=doc_gen_1["id"], attachment_name="sample_text.txt", auth=sg_user_session)
    client.update_doc(url=sg_url, db=sg_db, doc_id=doc_gen_1["id"], auth=sg_user_session)
    client.update_doc(url=sg_url, db=sg_db, doc_id=doc_gen_1["id"], auth=sg_user_session)

    parent_rev_list = ["2-foo2", doc_gen_1["rev"]]

    # Sync Gateway should error since it has no references attachment in its ancestors
    with pytest.raises(HTTPError) as he:
        client.add_conflict(
            url=sg_url,
            db=sg_db,
            doc_id=doc_gen_1["id"],
            parent_revisions=parent_rev_list,
            new_revision="3-foo3",
            auth=sg_user_session
        )
    assert he.value[0].startswith("400 Client Error: Bad Request for url: ")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
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

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper = ClusterKeywords()
    cluster_helper.reset_cluster(cluster_config, sg_conf)

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

    client.create_user(url=sg_url_admin, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels)
    sg_user_session = client.create_session(url=sg_url_admin, db=sg_db, name=sg_user_name)

    docs = client.add_docs(url=sg_url, db=sg_db, number=100, id_prefix=sg_db, channels=sg_user_channels, auth=sg_user_session)
    assert len(docs) == 100

    # Create doc with attachment and push to sync_gateway
    doc_with_att = document.create_doc(doc_id="att_doc", content={"sample_key": "sample_val"}, attachment_name="sample_text.txt", channels=sg_user_channels)

    client.add_doc(url=sg_url, db=sg_db, doc=doc_with_att, auth=sg_user_session)
    server = couchbaseserver.CouchbaseServer(cbs_url)

    # Assert that the attachment doc gets written to couchbase server
    server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att:")
    num_att_docs = len(server_att_docs)
    assert num_att_docs == 1
