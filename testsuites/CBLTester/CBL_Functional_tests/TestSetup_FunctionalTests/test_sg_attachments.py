import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode, replace_xattrs_sync_func_in_config
from keywords import document
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from CBLClient.Database import Database
from keywords import document, attachment
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.utils import host_for_url, log_info
from utilities.cluster_config_utils import get_cluster

@pytest.mark.channels
@pytest.mark.syncgateway
@pytest.mark.parametrize("source, target, num_of_docs", [
    # ('sg', 'sg', 10),
    # ('cbl', 'cbl', 100),
    ('sg', 'cbl', 10),
])
def test_delete_docs_with_attachments(params_from_base_test_setup, source, target, num_of_docs):
    """
    1. Have CBL and SG up and running
    2. Create docs with attachment on SG and CBL
    3. Replicate the docs
    4. Delete few docs in CBL and pull CBL docs
    5. Verify Attachments got deleted from the bucket
    """
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with sg version below 3.0.0')

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["attachment-cleanup11"]
    db = Database(base_url)
    sg_client = MobileRestClient()

    # 1. Have CBL and SG up and running
    sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    authenticator = Authenticator(base_url)

    # Create CBL database
    db.create_bulk_docs(num_of_docs, "attachment-cleanup111", db=cbl_db, channels=channels,attachments_generator=attachment.generate_png_100_100)

    # 2. push replication to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotes", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotes")
    session = cookie, session_id
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type="push-pull",
                                       replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session, include_docs=True)
    assert len(cbl_doc_ids) == len(sg_docs["rows"])
    print(sg_docs["rows"])
    sdk_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    print(sdk_doc_ids)
    raw_doc = sg_client.get_raw_doc(sg_admin_url, db=sg_db, doc_id=sdk_doc_ids[0])
    sg_sync_meta = raw_doc['_sync']
    print("************", sg_sync_meta)


    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']

    cbs_url = cluster_topology['couchbase_servers'][0]
    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    if ssl_enabled:
        connection_url = "couchbases://{}?ssl=no_verify".format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    bucket_name = 'travel-sample'
    sdk_client = get_cluster(connection_url, bucket_name)


    # 4. Delete docs in CBL/SG
    if target == "sg":
        sg_client.delete_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    else:
        db.cbl_delete_bulk_docs(cbl_db)

    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    # 5. Verify attachments are completely deleted from bucket on the SG
    ## TODO api needed

    raw_doc = sg_client.get_raw_doc(sg_admin_url, db=sg_db, doc_id=sdk_doc_ids[0])
    sg_sync_meta = raw_doc['_sync']
    print("************", sg_sync_meta)

    verify_sg_xattrs(mode,
                     sg_client,
                     sg_url=sg_admin_url,
                     sg_db=sg_db,
                     doc_id=sdk_doc_ids[0],
                     expected_number_of_revs=2,
                     expected_number_of_channels=len(channels),
                     deleted_docs=True
                     )
    raw_doc = sg_client.get_raw_doc(sg_admin_url, db=sg_db, doc_id=sdk_doc_ids[0])
    sg_sync_meta = raw_doc['_sync']
    print("************", sg_sync_meta)

    all_docs_via_sdk = sdk_client.get_multi(sdk_doc_ids)
    verify_doc_ids_in_sdk_get_multi(all_docs_via_sdk, 10 * 2, sdk_doc_ids)


def verify_doc_ids_in_sdk_get_multi(response, expected_number_docs, expected_ids):
    """ Verify 'expected_ids' are present in Python SDK get_multi() call """

    log_info('Verifing SDK get_multi response has {} docs with expected ids ...'.format(expected_number_docs))

    expected_ids_scratch_pad = list(expected_ids)
    assert len(expected_ids_scratch_pad) == expected_number_docs
    assert len(response) == expected_number_docs

    # Cross off all the doc ids seen in the response from the scratch pad
    for doc_id, value in list(response.items()):
        print(value.content)
        assert '_sync' not in value.content
        expected_ids_scratch_pad.remove(doc_id)

    # Make sure all doc ids have been found
    assert len(expected_ids_scratch_pad) == 0


@pytest.mark.channels
@pytest.mark.syncgateway
def test_doc_with_many_attachments(params_from_base_test_setup):
    """
    1. Have SG and CBL up and running
    2. Create a doc with lot of attachments on single document and replicate it to CBL
    3. Replicate to CBL/SG
    4. Delete few attachments and verify attachments are deleted in the bucket
    5. Delete the doc and verify all the attachments are deleted in the bucket
    """
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with sg version below 3.0.0')

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["attachments"]
    db = Database(base_url)
    sg_client = MobileRestClient()

    # 1. Have CBL and SG up and running
    sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 2. Add docs to SG/CBL.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    attachments_list = attachment.generate_5_png_10_10
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=1,
                                   attachments_generator=attachments_list, channels=channels)

    # 3.  Replicate to CBL/SG
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(cbl_db, target_url=sg_blip_url, continuous=True,
                                              replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)

    # 4 delete one of the attachment
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=cbl_doc_ids, number_updates=1, attachment_name=attachments_list[:3])

    # verify the deleted attachment

    # 5. Delete the document
    sg_client.delete_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)

    # 6. verify deleted documents attachments


    # 7. verify already delete document

    sg_client.delete_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)


@pytest.mark.channels
@pytest.mark.syncgateway
def test_restart_sg_creating_attachments(params_from_base_test_setup):
    """
    1.Have SG and CBL up and running
    2. Create docs with attachments
    3. Restart SG while documents are created
    4. verify documents are created
    5. Restart the sg while Deleting the docs
    7. verify all the attachments are deleted in the bucket
    """
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with sg version below 3.0.0')

    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag or test has enable delta sync')

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]

    channels = ["attachments"]
    db = Database(base_url)
    sg_client = MobileRestClient()
    num_of_docs = 1000

    # 1. Have CBL and SG up and running
    sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 2. Add docs to SG/CBL.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id
    attachments_list = attachment.generate_5_png_10_10
    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                   attachments_generator=attachments_list, channels=channels)
    sg_client.restart(config=sg_config, cluster_config=cluster_config)






def verify_sg_xattrs(mode, sg_client, sg_url, sg_db, doc_id, expected_number_of_revs, expected_number_of_channels, deleted_docs=False):
    """ Verify expected values for xattr sync meta data via Sync Gateway _raw """

    # Get Sync Gateway sync meta
    raw_doc = sg_client.get_raw_doc(sg_url, db=sg_db, doc_id=doc_id)
    sg_sync_meta = raw_doc['_sync']

    log_info('Verifying XATTR (expected num revs: {}, expected num channels: {})'.format(
        expected_number_of_revs,
        expected_number_of_channels,
    ))

    # Distributed index mode uses server's internal vbucket sequence
    # It does not expose this to the '_sync' meta
    if mode != 'di':
        assert isinstance(sg_sync_meta['sequence'], int)
        assert isinstance(sg_sync_meta['recent_sequences'], list)
        assert len(sg_sync_meta['recent_sequences']) == expected_number_of_revs

    assert isinstance(sg_sync_meta['cas'], str)
    assert sg_sync_meta['rev'].startswith('{}-'.format(expected_number_of_revs))
    assert isinstance(sg_sync_meta['channels'], dict)
    assert len(sg_sync_meta['channels']) == expected_number_of_channels
    assert isinstance(sg_sync_meta['time_saved'], str)
    assert isinstance(sg_sync_meta['history']['channels'], list)
    assert len(sg_sync_meta['history']['channels']) == expected_number_of_revs
    assert isinstance(sg_sync_meta['history']['revs'], list)
    assert len(sg_sync_meta['history']['revs']) == expected_number_of_revs
    assert isinstance(sg_sync_meta['history']['parents'], list)
