import pytest

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import random_string, get_embedded_asset_file_path
from CBLClient.Array import Array
from CBLClient.Blob import Blob
from CBLClient.Document import Document
from CBLClient.Dictionary import Dictionary
from CBLClient.Authenticator import Authenticator
from CBLClient.Replication import Replication
from libraries.testkit import cluster
from keywords.constants import RBAC_FULL_ADMIN


@pytest.mark.listener
@pytest.mark.replication
def test_doc_update_replication_with_blob_no_touch(params_from_base_test_setup):
    '''
    @summary:
    1. Create docs with blob in CBL
    2. Do push replication
    3. update docs in CBL, no touch for the enclosed blob
    4. Do push replication after docs update
    5. Verify docs are replicated successfully, and _attachments field on SG set correctly
    '''
    cbl_db = params_from_base_test_setup["source_db"]
    db = params_from_base_test_setup["db"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_db = "db"
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channels, auth=auth)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username, auth=auth)
    session = cookie, session_id

    # 1. Create a doc in CBL
    doc_handler = Document(base_url)
    str = random_string(length=3)
    doc_id = "cbl_blob_{}".format(str)
    doc = doc_handler.create(doc_id)

    # 1.1 set 2 string values
    doc_handler.setString(doc, "key1", "string value 1")
    doc_handler.setString(doc, "key2", "string value 2")

    # 1.2 set channels
    arr_handler = Array(base_url)
    chan_array = arr_handler.create()
    for ch in channels:
        arr_handler.addString(chan_array, ch)
    doc_handler.setArray(doc, "channels", chan_array)

    # 1.3 set 2 blobs
    blob_handler = Blob(base_url)
    string_to_utf8 = "CBL blob testing string"
    utf8_byte_array = blob_handler.createUTFBytesContent(content=string_to_utf8)
    blob1 = blob_handler.create(content_type="text/plain", content=utf8_byte_array)
    doc_handler.setBlob(doc, "blob1", blob1)

    # 1.4 save the doc to CBL db
    db.saveDocument(cbl_db, doc)

    # 2. Do push replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replicator_authenticator=replicator_authenticator,
                                              replication_type="push")
    replicator.wait_until_replicator_idle(repl, err_check=False)
    replicator.stop(repl)

    # validate the CBL doc has been pushed to SG
    sg_doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=session)
    assert sg_doc["blob1"]["content_type"] == "text/plain"

    # 3. Update the doc by adding a string value, no touch for the enclosed blobs
    new_doc = db.getDocument(cbl_db, doc_id)
    mutable_doc = doc_handler.toMutable(new_doc)
    doc_handler.setString(mutable_doc, "newkey1", "new string value 1")
    db.saveDocument(cbl_db, mutable_doc)

    # 4. Push replication again
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    replicator.stop(repl)

    # 5. Verify the doc replicated successfully, _attachments field on SG set correctly
    sg_doc = sg_client.get_doc(url=sg_admin_url, db=sg_db, doc_id=doc_id, auth=auth)
    assert "newkey1" in sg_doc
    assert sg_doc["newkey1"] == "new string value 1"
    assert sg_doc["blob1"]["content_type"] == "text/plain"
    assert "_attachments" in sg_doc


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("blob_data_type", [
    pytest.param('byte_array', marks=pytest.mark.ce_sanity),
    pytest.param('stream', marks=pytest.mark.sanity),
    'file_url'
])
def test_blob_contructor_replication(params_from_base_test_setup, blob_data_type):
    '''
    @summary:
    1. Create docs in CBL
    2. Do push replication
    3. update docs in CBL with attachment in specified blob type
    4. Do push replication after docs update
    5. Verify blob content replicated successfully
    '''
    cbl_db = params_from_base_test_setup["source_db"]
    db = params_from_base_test_setup["db"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_db = "db"
    num_of_docs = 10
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    if "c-" in liteserv_platform and blob_data_type == "file_url":
        pytest.skip('This test cannot run for C platforms')

    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channels, auth=auth)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username, auth=auth)
    # session = cookie, session_id

    # 1. Create docs in CBL
    db.create_bulk_docs(num_of_docs, "cbl_sync", db=cbl_db, channels=channels)

    # 2. Do push replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replicator_authenticator=replicator_authenticator,
                                              replication_type="push")
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    # Verify database doc counts
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # 3. update docs in CBL with attachment in specified blob type
    blob = Blob(base_url)
    dictionary = Dictionary(base_url)

    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id, doc_body in list(cbl_db_docs.items()):
        mutable_dictionary = dictionary.toMutableDictionary(doc_body)
        dictionary.setString(mutable_dictionary, "new_field_string_1", random_string(length=30))
        dictionary.setString(mutable_dictionary, "new_field_string_2", random_string(length=80))

        image_location = get_embedded_asset_file_path(liteserv_platform, db, cbl_db, "golden_gate_large.jpg")

        if blob_data_type == "byte_array":
            image_byte_array = blob.createImageContent(image_location, cbl_db)
            blob_value = blob.create("image/jpeg", content=image_byte_array)
        elif blob_data_type == "stream":
            image_stream = blob.createImageStream(image_location, cbl_db)
            blob_value = blob.create("image/jpeg", stream=image_stream)
        elif blob_data_type == "file_url":
            image_file_url = blob.createImageFileUrl(image_location)
            blob_value = blob.create("image/jpeg", file_url=image_file_url)

        dictionary.setBlob(mutable_dictionary, "new_field_blob", blob_value)
        doc_body_new = dictionary.toMap(mutable_dictionary)
        db.updateDocument(database=cbl_db, data=doc_body_new, doc_id=doc_id)

    # 4. Do push replication after docs update
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replicator_authenticator=replicator_authenticator,
                                              replication_type="push")

    replicator.stop(repl)

    # 5. Verify blob content replicated successfully
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    for doc_id, doc_body in list(cbl_db_docs.items()):
        sg_data = sg_client.get_doc(url=sg_admin_url, db=sg_db, doc_id=doc_id, auth=auth)
        assert "new_field_string_1" in sg_data, "Updated docs failed to get replicated"
        assert "new_field_string_2" in sg_data, "Updated docs failed to get replicated"
        assert "new_field_blob" in sg_data, "Updated docs failed to get replicated"
