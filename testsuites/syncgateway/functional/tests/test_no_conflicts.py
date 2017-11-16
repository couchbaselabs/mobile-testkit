import pytest

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from keywords.MobileRestClient import MobileRestClient
from keywords import document, attachment
from requests.exceptions import HTTPError
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
# from keywords.utils import log_info, host_for_url
# from concurrent.futures import ThreadPoolExecutor
# from couchbase.bucket import Bucket
# from keywords.constants import SDK_TIMEOUT


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('sync_gateway_revs_conflict_configurable', 10)
])
def test_no_conflicts_enabled(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """ @summary : Enable no conflicts and verify conflicts are not created
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
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sg_db = "db"

    if not no_conflicts_enabled:
        pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Create docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
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
    ('sync_gateway_revs_conflict_configurable', 1, 10),
    ('sync_gateway_revs_conflict_configurable', 10, 10)
])
def test_no_conflicts_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """ @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #4, #5
    Steps:
    1. Enable allow_conflicts = false in SG config with parametrized revs_limit
    2. Create docs to SG.
    3. Update the more than revs_limit.
    4. Creat a conflict and verifyit fails.
    5. Get number of revisions and verify length is equal to revs_limit set to
    6. Update the docs 1 more time
    7. Get number of revisions and verify number of revisions should be same as revs_limit
    8. Verify previous revisions does not exist
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    if not no_conflicts_enabled:
        pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 1. Enable allow_conflicts = false in SG config with revs_limit=1
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
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
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(4):
            assert prev_revs[i] not in num_of_revs

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)

    # 7. Get number of revisions and verify number of revisions should be same revs_limit
    # 8. Verify previous revisions does not exist
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(5):
            assert prev_revs[i] not in num_of_revs


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 1, 5)
])
def test_no_conflicts_update_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """ @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #14
    Steps:
    1. Enable allow_conflicts = false in SG config with revs_limit=5
    2. Create docs to SG.
    3. Update the more than revs_limit.
    4. Check the revision list for the doc.
    5. Modify the revs_limit to 2
    6. Update doc
    7. Verify the revision history shows only 2 revisions now
    8. Verify previous revsions deleted
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    reduced_revs_limit = revs_limit - 3
    total_updates = revs_limit + 5

    if not no_conflicts_enabled:
        pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 1. Enable allow_conflicts = false in SG config with revs_limit=5
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 1 with no conflicts mode"

    # 2. Create docs to SG.
    # sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
    #                                     attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(total_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(5):
            assert prev_revs[i] not in num_of_revs

    # 5. Modify the revs_limit to 2
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', reduced_revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 2 with no conflicts mode"

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=2, delay=None, auth=autouser_session, channels=channels)

    # 7. Get number of revisions and verify number of revisions is equvalent to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == 2, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(total_updates - reduced_revs_limit):
            assert prev_revs[i] not in num_of_revs


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit, additional_updates", [
    ('sync_gateway_revs_conflict_configurable', 10, 25, 5),
    ('sync_gateway_revs_conflict_configurable', 10, 1000, 1000)
])
def test_conflicts_sg_accel_added(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit, additional_updates):
    """ @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #12, #16, #21
    Steps:
    1. Enable allow_conflicts = false in SG config with revs_limit
    2. Create docs to SG.
    3. Update the docs few times and get all revisions of updates
    4. Get number of revisions and verify length is equal to revs_limit set to
    5. Start sg accel
    6. Update the docs with few updates
    7. Get number of revisions and verify number of revisions is equvalent to revs_limit set to
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    total_updates = revs_limit + additional_updates
    new_updates = 2

    if mode != "di":
        pytest.skip('--no-conflicts is not enabled or mode is not di, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)
    c.sg_accels[0].stop()

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 1. Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit  with no conflicts mode"

    # 2. Create docs to SG.
    # sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
    #                                     attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times and get all revisions of updates
    prev_revs = []
    for i in xrange(total_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Get number of revisions and verify length is equal to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(additional_updates):
            assert prev_revs[i] not in num_of_revs

    # 5. Start sg accel
    status = c.sg_accels[0].start(config=sg_conf)
    assert status == 0, "sync_gateway accel did not start"

    # 6. Update the docs with few updates
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=new_updates, delay=None, auth=autouser_session, channels=channels)

    # 7. Get number of revisions and verify number of revisions is equvalent to revs_limit set to
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(additional_updates + new_updates):
            assert prev_revs[i] not in num_of_revs


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 1, None),
    ('sync_gateway_revs_conflict_configurable', 1, 10),
    ('sync_gateway_revs_conflict_configurable', 1, 1)
])
def test_migrate_conflicts_to_noConflicts(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """ @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #6
    Steps:
    1. Start sg with default(i.e allow_conflicts=true)
    2. Create docs to SG.
    3. Update docs few times .
    4. Create a conflicts and verify it is successful.
    5. Modify sg config by enabling allow_conflicts to false
    6. restart sg.
    7. Create a conflict and verify conflict throws 409.
    8. update docs few number of times.
    9. Verify it can maintain default revisions.
    10. Verify previous revisions deleted.
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    if revs_limit is None:
        revs_limit = 1000
    additional_updates = revs_limit

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    # 1. Start sg with default(i.e allow_conflicts=true)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Create docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Create a conflicts and verify it is successful.
    for doc in sg_docs:
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                                auth=autouser_session)
        assert conflicted_rev["rev"] == "2-foo"

    # 5. Enable allow_conflicts = false in SG config and 6. restart sg
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'no_conflicts_enabled', "True", property_name_check=False)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=autouser_session, channels=channels)

    # 7. Create a conflict and verify conflict throws 409.
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo1",
                                   auth=autouser_session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # 8. update docs few number of times.
    update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=additional_updates,
                                           auth=autouser_session, channels=channels)

    # 9. Verify it can maintain default revisions.
    # 10. Verify previous revisions deleted.
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(additional_updates):
            assert prev_revs[i] not in num_of_revs


"""
@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 1, 10),
    # ('sync_gateway_revs_conflict_configurable', 1, 1)
])
def test_concurrent_updates_no_conflicts(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
     @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #6
    Steps:
    1. Start sg with default(i.e allow_conflicts=true)
    2. Create docs to SG.
    3. Update docs few times .
    4. Create a conflicts and verify it is successful.
    5. Modify sg config by enabling allow_conflicts to false
    6. restart sg.
    7. Create a conflict and verify conflict throws 409.
    8. update docs few number of times.
    9. Verify it can maintain default revisions.
    10. Verify previous revisions deleted.


    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    if revs_limit is None:
        revs_limit = 1000
    additional_updates = revs_limit

    if not no_conflicts_enabled:
        pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 1. Start sg with default(i.e allow_conflicts=true)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Create docs to SG.
    # sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
    #                                     attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # Connect to server via SDK
    log_info('Connecting to bucket ...')
    bucket_name = 'data-bucket'
    cbs_url = topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)
    sg_doc_ids = [doc['id'] for doc in sg_docs]
    sdk_docs_resp = sdk_client.get_multi(sg_doc_ids)
    log_info(">>><<< sdk docs resp {}".format(sdk_docs_resp))

    # Update the same documents concurrently from a sync gateway client and and sdk client
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_sg_task = tpe.submit(sg_client.update_doc, url=sg_url, db=sg_db, docs=sg_docs, number_updates=1,
                                         delay=None, auth=autouser_session, channels=channels)


        update_from_sdk_task = tpe.submit(
            update_sdk_docs,
            client=sdk_client,
            docs_to_update=all_doc_ids,
            prop_to_update=sdk_tracking_prop,
            number_updates=number_updates_per_doc_per_client
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        update_from_sg_task.result()
        update_from_sdk_task.result()

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Create a conflicts and verify it is successful.
    for doc in sg_docs:
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                                auth=autouser_session)
        assert conflicted_rev["rev"] == "2-foo"

    # 5. Enable allow_conflicts = false in SG config and 6. restart sg
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'no_conflicts_enabled', "True", property_name_check=False)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=autouser_session, channels=channels)

    # 7. Create a conflict and verify conflict throws 409.
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo1",
                                   auth=autouser_session)
        assert he.value.message.startswith('409 Client Error: Conflict for url:')

    # 8. update docs few number of times.
    update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=additional_updates,
                                           auth=autouser_session, channels=channels)

    # 9. Verify it can maintain default revisions.
    # 10. Verify previous revisions deleted.
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(additional_updates):
            assert prev_revs[i] not in num_of_revs
    """
