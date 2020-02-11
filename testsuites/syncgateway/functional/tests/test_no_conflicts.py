import pytest
import time

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from keywords.MobileRestClient import MobileRestClient
from keywords import document, attachment
from requests.exceptions import HTTPError
from couchbase.exceptions import KeyExistsError
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.utils import log_info, host_for_url
from concurrent.futures import ThreadPoolExecutor
from couchbase.bucket import Bucket
from keywords.constants import SDK_TIMEOUT


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
    2. Add docs to SG.
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

    # 2. Add docs to SG.
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
        assert str(he.value).startswith('409 Client Error: Conflict for url:')

    # 6. Update the docs 1 more time
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 10, 1),
    ('sync_gateway_revs_conflict_configurable', 10, 10)
])
def test_no_conflicts_with_revs_limit(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """ @summary Enable no conflicts and  with non default revs_limit and verify revs_limit is maintained
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #4, #5
    Steps:
    1. Enable allow_conflicts = false in SG config with parametrized revs_limit
    2. Add docs to SG.
    3. Update docs more than revs_limit.
    4. Create a conflict and verify it fails.
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

    # 1. Enable allow_conflicts = false in SG config with revs_limit
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after having revs_limit 1 with no conflicts mode"

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit + 5):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Try to create a conflict
    for doc in sg_docs:
        with pytest.raises(HTTPError) as he:
            sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                   auth=autouser_session)
        assert str(he.value).startswith('409 Client Error: Conflict for url:')

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
    1. Enable allow_conflicts = false in SG config with parametried revs_limit
    2. Add docs to SG.
    3. Update the more than revs_limit.
    4. Check the revision list for the doc.
    5. Modify the revs_limit to 2
    6. Update doc
    7. Verify the revision history shows only 2 revisions now
    8. Verify previous revisions deleted
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

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(total_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=autouser_session, channels=channels)
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

    # 7. Get number of revisions and verify number of revisions is equivalent to revs_limit set to
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
    """ @summary Verify no conflicts feature works with sg accel down
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #12, #16, #21
    Steps:
    1. Enable allow_conflicts = false in SG config with revs_limit
    2. Add docs to SG.
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
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sg_db = "db"
    total_updates = revs_limit + additional_updates
    new_updates = 2

    if not no_conflicts_enabled or mode != "di":
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

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times and get all revisions of updates
    prev_revs = []
    for i in xrange(total_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=autouser_session, channels=channels)
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
    """ @summary Migrating from no conflicts false to true
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #6, #7, #8
    Steps:
    1. Start sg with default(i.e allow_conflicts=true)
    2. Add docs to SG.
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
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_db = "db"

    if revs_limit is None:
        revs_limit = 1000
    additional_updates = revs_limit

    if no_conflicts_enabled or sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    # 1. Start sg with default(i.e allow_conflicts=true)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(revs_limit):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=autouser_session, channels=channels)
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
        assert str(he.value).startswith('409 Client Error: Conflict for url:')

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


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 100, 10),
    ('sync_gateway_revs_conflict_configurable', 100, 10),
    ('sync_gateway_revs_conflict_configurable', 1000, 100),
    ('sync_gateway_revs_conflict_configurable', 10, 1000),
])
def test_concurrent_updates_no_conflicts(params_from_base_test_setup, sg_conf_name, num_of_docs, revs_limit):
    """@summary Test with concurrent updates with no conflicts enabled
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #15
    Steps:
    1. Start sg with some revs_limit specified
    2. Add docs to SG.
    3. Update docs few times via sg .
    4. Update docs few times vis sdk concurrently with sg.
        -> There are chances of getting conflict errors on both, handled the error appropriately
    5. update docs few number of times.
    6. Verify it can maintain default revisions.
    7. Verify previous revisions deleted and revisions maintained based on revs_limit
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
    total_updates = revs_limit + additional_updates
    if not no_conflicts_enabled:
        pytest.skip('--no-conflicts is not enabled, so skipping the test')
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # 1. Start sg
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')

    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    # end of Set up

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # Connect to server via SDK
    log_info('Connecting to bucket ...')
    bucket_name = 'data-bucket'
    cbs_url = topology['couchbase_servers'][0]
    cbs_ip = host_for_url(cbs_url)
    if c.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)
    sg_doc_ids = [doc['id'] for doc in sg_docs]
    sdk_docs_resp = sdk_client.get_multi(sg_doc_ids)

    # Update the same documents concurrently from a sync gateway client and and sdk client
    with ThreadPoolExecutor(max_workers=9) as tpe:

        update_from_sdk_task = tpe.submit(sdk_bulk_update, sdk_client, sdk_docs_resp, 10)
        update_from_sg_task = tpe.submit(sg_doc_updates, sg_client, sg_url=sg_url, sg_db=sg_db, sg_docs=sg_docs, number_updates=10,
                                         auth=autouser_session, channels=channels)

        update_from_sg_task.result()
        update_from_sdk_task.result()

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(total_updates):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None,
                                               auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Verify it can maintain default revisions.
    # 5. Verify previous revisions deleted.
    for doc in sg_docs:
        num_of_revs = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert len(num_of_revs) == revs_limit, "Number of revisions in history is more than revs_limit set in sg config"
        for i in xrange(additional_updates):
            assert prev_revs[i] not in num_of_revs


def sg_doc_updates(sg_client, sg_url, sg_db, sg_docs, number_updates, auth, channels):
    for doc in sg_docs:
        try:
            sg_client.update_doc(sg_url, sg_db, doc['id'], number_updates, auth=auth, channels=channels)
        except HTTPError as e:
            if e.response.status_code == 409 and str(e).startswith('409 Client Error: Conflict for url:'):
                log_info("Got conflict with sdk update, skip it")


def sdk_bulk_update(sdk_client, sdk_docs, num_of_updates):
    for doc_id, val in sdk_docs.items():
        doc_body = val.value
        doc_body["updated_by_sdk"] = 0
        for i in range(num_of_updates):
            doc_body["updated_by_sdk"] += 1
            try:
                sdk_client.upsert(doc_id, doc_body)
            except KeyExistsError:
                log_info('CAS mismatch from SDK. Will retry ...')


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('sync_gateway_revs_conflict_configurable', 10)
])
def test_migrate_conflicts_delete_last_rev(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """ @summary Migrate conflicts to no-conflicts mode and delete last revision and verify revisions exists in open revisions
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #19
    Steps:
    1. Start sg with default(i.e allow_conflicts=true)
    2. Add docs to SG.
    3. Update docs few times .
    4. Create a conflicts and verify it is successful.
    5. Modify sg config by enabling allow_conflicts to false
    6. restart sg.
    7. Delete doc by revision of current active open revision
    8. Verify tombstoned doc is identified as deleted in open revision ids
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

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

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Update the docs few times
    prev_revs = []
    for i in xrange(25):
        update_sg_docs = sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, delay=None, auth=autouser_session, channels=channels)
        rev = update_sg_docs[0]['rev'].split('-')[1]
        prev_revs.append(rev)

    # 4. Create a conflicts and verify it is successful.
    for doc in sg_docs:
        conflicted_rev = sg_client.add_conflict(url=sg_url, db=sg_db, doc_id=doc["id"], parent_revisions=doc["rev"], new_revision="2-foo",
                                                auth=autouser_session)
        assert conflicted_rev["rev"] == "2-foo"
    time.sleep(5)

    # 5. Enable allow_conflicts = false in SG config and 6. restart sg
    revs_limit = 21
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'no_conflicts_enabled', "True", property_name_check=False)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = c.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after no conflicts is enabled"
    sg_client.update_docs(url=sg_url, db=sg_db, docs=sg_docs, number_updates=1, auth=autouser_session, channels=channels)

    # 6. Delete doc by revision of current active open revision
    # 7.Verify tombstoned doc is identified as deleted in open revision ids
    for doc in sg_docs:
        num_of_revs = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        deleted_doc = sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc["id"], rev=num_of_revs["_rev"], auth=autouser_session)
        num_of_revs_history = sg_client.get_revs_num_in_history(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert "foo" in num_of_revs_history, "conflicted revision does not exist in revision history"
        deleted_open_rev_ids = sg_client.get_deleted_open_rev_ids(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)
        assert deleted_doc["rev"] in deleted_open_rev_ids, "open rev ids list is not identified as deleted for tombstoned doc "


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('sync_gateway_revs_conflict_configurable', 5),
    ('sync_gateway_revs_conflict_configurable', 100),
    ('sync_gateway_revs_conflict_configurable', 900)
])
def test_revs_cache_size(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """ @summary Test for no-conflicts with rev_cache size
    Test case link : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    covered #18
    Steps:
    Note : the sg config have rev_cache_size as 1000 , make sure number of docs is less than 1000 to have the test
    work with expected behavior
    1. Add docs to SG.
    2. Get the docs
    3. Verify number of rev_cache_hits is same as number of docs if rev_cache_size is more than number of docs.
    """

    # Setup
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    retrieved_docs = num_of_docs / 2
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.0":
        pytest.skip('It is enabled and does not work with sg < 2.0 , so skipping the test')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    sg_client = MobileRestClient()
    channels = ["no-conflicts"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')
    # end of Set up

    # 2. Add docs to SG.
    sgdoc_bodies = document.create_docs(doc_id_prefix="sg_docs", number=num_of_docs, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # 3. Get all docs
    for i in range(retrieved_docs):
        doc = sg_docs[i]
        sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc["id"], auth=autouser_session)

    # 4. Verify there are number of hits should be same as retrieved docs
    exp_vars = sg_client.get_expvars(url=sg_admin_url)
    if sync_gateway_version < "2.5":
        revision_cache_hits = exp_vars["syncGateway_stats"]["revisionCache_hits"]
        revision_cache_misses = exp_vars["syncGateway_stats"]["revisionCache_misses"]
    else:
        revision_cache_hits = exp_vars["syncgateway"]["per_db"][sg_db]["cache"]["rev_cache_hits"]
        revision_cache_misses = exp_vars["syncgateway"]["per_db"][sg_db]["cache"]["rev_cache_misses"]
    assert revision_cache_hits == retrieved_docs, "Revision Cache hits did not hit with expected number {}".format(num_of_docs)
    assert revision_cache_misses == 0, "Revision Cache misses is not 0"
