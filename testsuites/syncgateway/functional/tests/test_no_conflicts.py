import pytest

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster, syncgateway
from keywords.MobileRestClient import MobileRestClient
from keywords import document, attachment
from keywords.utils import log_info
from requests.exceptions import HTTPError
from utilities.cluster_config_utils import persist_cluster_config_environment_prop


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('sync_gateway_revs_conflict_configurable', 10)
])
def test_no_conflicts_(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """ @summary : Enable no conflicts and verify conflicts are not creaed
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #3
    Steps:
    1. Enable allow_conflicts = false in SG config
    2. Create docs to SG.
    3. Update the docs few times.
    4. Try to create a conflict.
    5. Check the revision list for the doc 
    6. Verify no conflicts can be created.
    7. Sync Gateway should respond with a 409 upon trying to add a conflict
    8. Should be possible to add more than 1 revision (Default revs_limit = 1000)
    """
    
    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Create docs to SG.
    def update_props():
        return {'updates': 0,
                }
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs, 
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    sg_doc_ids = [doc['_id'] for doc in sgdoc_bodies]
    assert len(sgdoc_bodies) == num_of_docs
    
    # 3. Update the docs few times
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=3, delay=None, auth=autouser_session, channels=channels)
   
    # 4. Try to create a conflict
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                   auth=autouser_session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    # ('sync_gateway_revs_conflict_configurable', 1, 10),
    ('sync_gateway_revs_conflict_configurable', 10, 10)
])
def test_no_conflicts_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """ Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #4, #5
    Steps:
    1. Enable allow_conflicts = false in SG config with revs_limit=1
    2. Create docs to SG.
    3. Update the more than revs_limit.
    4. Check the revision list for the doc.
    5. Verify revs_limit shows only 1.
    6. Create a conflic t
    """
    
    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    no_conflicts_enabled =  params_from_base_test_setup["no_conflicts_enabled"]
    sg_db = "db"

    # if not no_conflicts_enabled:
    #    pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 1. Enable allow_conflicts = false in SG config with revs_limit=1
    persist_cluster_config_environment_prop(cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 1 with no conflicts mode"
    
    # 2. Create docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs
    
    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit + 5):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Try to create a conflict
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                   auth=autouser_session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # 5. Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_open_revs_ids(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(4):
            assert prev_revs[i] not in num_of_revs

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)

    # 7. Get number of revisions and verify number of revisions 1 more than number of updates
    for doc in sg_docs:
        num_of_revs = sg_client.get_open_revs_ids(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(5):
            assert prev_revs[i] not in num_of_revs
