
import pytest
import subprocess
import time

from requests.exceptions import HTTPError
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway
from keywords.userinfo import UserInfo
from keywords.utils import host_for_url, log_info
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import get_cluster
from keywords.remoteexecutor import RemoteExecutor
from utilities.cluster_config_utils import load_cluster_config_json
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from keywords.constants import RBAC_FULL_ADMIN


@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.oscertify
@pytest.mark.parametrize('sg_conf_name', [
    'xattrs/mobile_opt_in'
])
def test_mobile_opt_in(params_from_base_test_setup, sg_conf_name):
    """
    Scenario: Enable mobile opt in sync function in sync-gateway configuration file
    - Check xattrs/mobile-opt-in_cc or di json files
    - 8 cases covered
    - doc : https://docs.google.com/document/d/1XxLIBsjuj_UxTTJs4Iu7C7uZdos8ZEzeckrVc17y3sw/edit
    - #1 Create doc via sdk with mobile opt in and verify doc is imported
    - #2 Create doc via sdk with mobile opt out and verify doc is not imported
    - #3 Create doc via sg with mobile opt in and update via sdk and verify doc is imported
    - #4 Create doc via sg with mobile opt out and update via sdk and verify doc is not imported
         - Try to update same doc via sg and verify 409 conflict error is thrown
         - Create a doc with same doc id and verify doc is created successfully
    - #5 Create doc via sg with mobile opt out and update via sdk which created no revisions
         - Now do sdk create with mobile opt in should import case #5
    - #6 Create doc via sg with mobile opt out  and update via sdk with opt in
         - Verify type is overrided and doc is imported
    - #7 Create doc via sg with mobile opt in  and update via sdk with opt out
         - Verify type is overrided and doc is not imported
    - #8 Disable import in the sg config and have mobile opt in function
         Create doc via sdk with mobile property and verify sg update succeeds
    - #9 Same config as #8 and have mobile opt in function in config
         Create doc via sdk without mobile property and create new doc via sg with same doc id and
         verify it succeeds
    """

    # bucket_name = 'data-bucket'
    sg_db = 'db'

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    buckets = get_buckets_from_sync_gateway_config(sg_conf, cluster_conf)
    bucket_name = buckets[0]

    # Create clients
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    cbs_ip = host_for_url(cbs_url)
    if cluster.ipv6:
        connection_url = 'couchbase://{}?ipv6=allow'.format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    sdk_client = get_cluster(connection_url, bucket_name)
    # Create user / session
    auto_user_info = UserInfo(name='autotest', password='pass', channels=['mobileOptIn'], roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        password=auto_user_info.password,
        channels=auto_user_info.channels,
        auth=auth
    )

    test_auth_session = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        auth=auth
    )

    def update_mobile_prop():
        return {
            'updates': 0,
            'type': 'mobile',
        }

    def update_non_mobile_prop():
        return {
            'updates': 0,
            'test': 'true',
            'type': 'mobile opt out',
        }

    # Create first doc via SDK with type mobile. Case #1
    doc_id1 = 'mobile_opt_in_sdk_doc'
    doc = document.create_doc(doc_id=doc_id1, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    sdk_client.upsert(doc_id1, doc)
    sg_get_doc1 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id1, auth=test_auth_session)
    assert sg_get_doc1['_rev'].startswith('1-') and sg_get_doc1['_id'] == doc_id1
    # Additional coverage for case #1
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id1, number_updates=1, auth=test_auth_session)
    sg_get_doc1 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id1, auth=test_auth_session)
    assert sg_get_doc1['_rev'].startswith('2-') and sg_get_doc1['_id'] == doc_id1

    # Create second doc via SDK with type non mobile. Case #2
    doc_id2 = 'mobile_opt_out_sdk_doc'
    doc = document.create_doc(doc_id=doc_id2, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    sdk_client.upsert(doc_id2, doc)
    with pytest.raises(HTTPError) as he:
        sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id2, auth=test_auth_session)
    log_info(he.value)
    resp = str(he.value)
    assert resp.startswith('404 Client Error: Not Found for url:')

    # Create third sg doc with mobile opt in  and update via sdk. Case #3
    doc_id3 = 'mobile_opt_in_sg_doc'
    doc_body = document.create_doc(doc_id=doc_id3, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    sg_get_doc3 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id3, auth=test_auth_session)
    sg_get_doc3["updated_sdk_via_sg"] = "1"
    sdk_client.upsert(doc_id3, sg_get_doc3)
    sg_get_doc3 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id3, auth=test_auth_session)
    assert sg_get_doc3['_rev'].startswith('2-') and sg_get_doc3['_id'] == doc_id3
    log_info("sg get doc3 is {}".format(sg_get_doc3))

    # Create fourth sg doc with mobile opt out and update via sdk. Case #4 and case #8
    doc_id4 = 'mobile_opt_out_sg_doc'
    doc_body = document.create_doc(doc_id=doc_id4, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    # update vis SDK
    sg_get_doc4 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id4, auth=test_auth_session)
    rev = sg_get_doc4['_rev']
    sg_get_doc4["updated_sdk_via_sg"] = "1"
    sdk_client.upsert(doc_id4, sg_get_doc4)
    with pytest.raises(HTTPError) as he:
        sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id4, auth=test_auth_session)
    log_info(he.value)
    resp = str(he.value)
    assert resp.startswith('404 Client Error: Not Found for url:')
    # update via SG
    with pytest.raises(HTTPError) as he:
        sg_client.put_doc(url=sg_url, db=sg_db, doc_id=doc_id4, doc_body={'sg_rewrite': 'True'}, rev=rev, auth=test_auth_session)
    log_info(he.value)
    resp = str(he.value)
    assert resp.startswith('409 Client Error: Conflict for url:')
    # Create same doc again to verify there is not existing key error covers case #8
    doc_body = document.create_doc(doc_id=doc_id4, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    sg_get_doc4_1 = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    log_info("4th doc after recreate vis sg is {}".format(sg_get_doc4_1))
    assert sg_get_doc4_1['rev'].startswith('1-') and sg_get_doc4_1['id'] == doc_id4

    # Create Fifth sg doc with mobile opt in and delete doc which created no revisions i.e tombstone doc
    # Now do sdk create with mobile opt in should import case #5
    doc_id5 = 'mobile_sdk_recreate_no_activerev'
    doc_body = document.create_doc(doc_id=doc_id5, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    rev = doc['rev']
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id5, rev=rev, auth=test_auth_session)
    # At this point no active revisions for this doc, so now update via sdk with mobile opt in should be successful
    # in getting doc
    doc = document.create_doc(doc_id=doc_id5, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    sdk_client.upsert(doc_id5, doc)
    sg_get_doc5 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id5, auth=test_auth_session)
    log_info("sg get doc 5 is {}".format(sg_get_doc5))
    assert sg_get_doc5['_rev'].startswith('1-') and sg_get_doc5['_id'] == doc_id5

    # Create sixth sg doc with mobile opt out  and update via sdk with opt in
    doc_id6 = 'mobileoptout_sg_doc_sdkupdate_optin'
    doc_body = document.create_doc(doc_id=doc_id6, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    sg_get_doc6 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id6, auth=test_auth_session)
    log_info("Sg sixth doc is {}".format(sg_get_doc6))
    sg_get_doc6["type"] = "mobile"
    sdk_client.upsert(doc_id6, sg_get_doc6)
    sg_get_doc6 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id6, auth=test_auth_session)
    assert sg_get_doc6['_rev'].startswith('2-') and sg_get_doc6['_id'] == doc_id6

    # Create seventh sg doc with mobile opt in  and update via sdk with opt out
    doc_id7 = 'mobileoptin_sg_doc_sdkupdate_optout'
    doc_body = document.create_doc(doc_id=doc_id7, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    sg_get_doc7 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id7, auth=test_auth_session)
    log_info("Sg sixth doc is {}".format(sg_get_doc7))
    sg_get_doc7["type"] = "mobile opt out"
    sdk_client.upsert(doc_id7, sg_get_doc7)
    with pytest.raises(HTTPError) as he:
        sg_get_doc7 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id7, auth=test_auth_session)
    log_info(he.value)
    resp = str(he.value)
    assert resp.startswith('404 Client Error: Not Found for url:')
    # TODO : verify _changes that it shows tombstone revisions -> it will happen on 2.0

    # Create eighth sdk doc with import disabled and add mobile property and update via sg. Case #7
    sg_conf_name = "xattrs/mobile_opt_in_no_import"
    sg_no_import_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_util = SyncGateway()
    sg_util.start_sync_gateways(cluster_config=cluster_conf, url=sg_url, config=sg_no_import_conf)

    doc_id8 = 'mobile_opt_in_sg_rewrite_with_importdisabled'
    doc_body = document.create_doc(doc_id=doc_id8, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    sdk_client.upsert(doc_id8, doc_body)
    with pytest.raises(HTTPError) as he:
        sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    log_info(he.value)
    assert str(he.value).startswith('409 Client Error: Conflict for url:')
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id8, number_updates=1, auth=test_auth_session)
    sg_get_doc8 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id8, auth=test_auth_session)
    assert sg_get_doc8['_rev'].startswith('2-') and sg_get_doc8['_id'] == doc_id8

    # Create ninth sdk doc with import disabled and add mobile property and update via sg. Case #8
    doc_id9 = 'mobile_opt_out_sg_rewrite_with_importdisabled'
    doc_body = document.create_doc(doc_id=doc_id9, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    sdk_client.upsert(doc_id9, doc_body)
    sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    # sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id8, number_updates=1, auth=test_auth_session)
    sg_get_doc9 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id9, auth=test_auth_session)
    assert sg_get_doc9['_rev'].startswith('1-') and sg_get_doc9['_id'] == doc_id9


@pytest.mark.parametrize('sg_conf_name', [
    'log_rotation_new'
])
def test_non_mobile_ignore_count(params_from_base_test_setup, sg_conf_name):
    """
    Scenario: Enable mobile opt in sync function in sync-gateway configuration file
    1. Create doc in CBS with xattrs off and verify doc is not imported
    2. Verify “non_mobile_ignored_count” is 0 on _expvar end point
    3. Create another document('abc') on CBS and verify it is not imported and verify that info logs generate the log
        “Cache: changeCache: Doc “abc” does not have valid sync data”
    4. Verify “non_mobile_ignored_count” is 1 on _expvar end point
    5. Create another document('xyz') and verify log is generated and “non_mobile_ignored_count” is 2
    6. Restart SGW , Verify “non_mobile_ignored_count” is 0
    7. Create document('def') and verify info logs show the message “Cache: changeCache: Doc “def” does not have valid sync data”
       verify “non_mobile_ignored_count” is 1
    8. Verify warn_count is 0
    """

    # bucket_name = 'data-bucket'
    sg_db = 'db'

    cluster_config = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    sg_platform = params_from_base_test_setup['sg_platform']
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    disable_persistent_config = params_from_base_test_setup["disable_persistent_config"]

    # This test should only run when using xattr meta storage
    if xattrs_enabled or sync_gateway_version < "3.0":
        pytest.skip('Cannot run with --xattrs flag')

    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_config))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config, use_config=True)
    buckets = get_buckets_from_sync_gateway_config(sg_config, cluster_config)
    bucket_name = buckets[0]

    # Create clients
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    cbs_ip = host_for_url(cbs_url)
    if cluster.ipv6:
        connection_url = 'couchbase://{}?ipv6=allow'.format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    sdk_client = get_cluster(connection_url, bucket_name)

    # Create user / session
    auto_user_info = UserInfo(name='autotest', password='pass', channels=['mobileOptIn'], roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        password=auto_user_info.password,
        channels=auto_user_info.channels,
        auth=auth
    )

    test_auth_session = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        auth=auth
    )

    if sg_platform == "windows":
        json_cluster = load_cluster_config_json(cluster_config)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip)

    # 1. Create doc in CBS with xattrs off and verify doc is not imported
    doc_id1 = 'non_mobile_ignore_1'
    doc = document.create_doc(doc_id=doc_id1, channels=['non_mobile_ignore'])
    sdk_client.upsert(doc_id1, doc)
    try:
        sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id1, auth=test_auth_session)
        assert False, "doc imported to sync gateway with xttars on"
    except HTTPError as e:
        log_info("Got the Http error".format(e))

    # 2. Verify “non_mobile_ignored_count” is 0 on _expvar end point
    sg_expvars = sg_client.get_expvars(url=sg_admin_url, auth=auth)
    non_mobile_ignore_count = sg_expvars["syncgateway"]["per_db"][sg_db]["cache"]["non_mobile_ignored_count"]
    warn_count = sg_expvars["syncgateway"]["global"]["resource_utilization"]["warn_count"]
    assert non_mobile_ignore_count == 1, "non_mobile_ignore_count did not get expected count"
    command = "grep 'Cache: changeCache' /tmp/sg_logs/sg_info.log | wc -l"
    command1 = "grep 'does not have valid sync data' /tmp/sg_logs/sg_info.log | wc -l"
    if "macos" in sg_platform:
        stdout = subprocess.check_output(command, shell=True)
        log1_num = int(stdout)
        stdout = subprocess.check_output(command1, shell=True)
        log2_num = int(stdout)
    else:
        _, stdout, _ = remote_executor.execute(command)
        log1_num = int(stdout[0])
        _, stdout, _ = remote_executor.execute(command1)
        log2_num = int(stdout[0])

    # 3. Create another document('abc') on CBS and verify it is not imported and verify that info logs generate the log
    #    “Cache: changeCache: Doc “abc” does not have valid sync data”
    doc_id2 = 'non_mobile_ignore_2'
    doc = document.create_doc(doc_id=doc_id2, channels=['non_mobile_ignore'])
    sdk_client.upsert(doc_id2, doc)

    if "macos" in sg_platform:
        time.sleep(2)
        stdout = subprocess.check_output(command, shell=True)
        assert int(stdout) == 1 + log1_num, "did not find the expected match on sg info logs"
        stdout = subprocess.check_output(command1, shell=True)
        assert int(stdout) == 1 + log2_num, "did not find the expected match on sg info logs"
    else:
        if sg_platform == "windows":
            command = "grep 'Cache: changeCache' C:\\\\tmp\\\\sg_logs\sg_info.log | wc -l"
            command1 = "grep 'does not have valid sync data' C:\\\\tmp\\\\sg_logs\sg_info.log | wc -l"
        _, stdout, _ = remote_executor.execute(command)
        assert int(stdout[0]) == 1 + log1_num, "did not find the expected match on sg info logs"
        _, stdout, _ = remote_executor.execute(command1)
        assert int(stdout[0]) == 1 + log2_num, "did not find the expected match on sg info log"

    # 4. Verify “non_mobile_ignored_count” is 1 on _expvar end point
    count = 0
    retry_count = 5
    while count < retry_count:
        sg_expvars = sg_client.get_expvars(url=sg_admin_url, auth=auth)
        non_mobile_ignore_count = sg_expvars["syncgateway"]["per_db"][sg_db]["cache"]["non_mobile_ignored_count"]
        if non_mobile_ignore_count == 2:
            break
        else:
            time.sleep(1)
            count += 1
    assert non_mobile_ignore_count == 2, "non_mobile_ignore_count did not get expected count"

    # 6. Restart SGW , Verify “non_mobile_ignored_count” is 0
    status = cluster.sync_gateways[0].restart(config=sg_config, cluster_config=cluster_config, use_config=True)
    assert status == 0, "Syncgateway did not restart "

    if "macos" in sg_platform:
        stdout = subprocess.check_output(command, shell=True)
        log1_num = int(stdout)
        stdout = subprocess.check_output(command1, shell=True)
        log2_num = int(stdout)
    else:
        _, stdout, _ = remote_executor.execute(command)
        log1_num = int(stdout[0])
        _, stdout, _ = remote_executor.execute(command1)
        log2_num = int(stdout[0])
    # 7. Create document('def') and verify info logs show the message “Cache: changeCache: Doc “def” does not have valid sync data”
    #    verify “non_mobile_ignored_count” is 1
    doc_id3 = 'non_mobile_ignore_3'
    doc = document.create_doc(doc_id=doc_id3, channels=['non_mobile_ignore'])
    sdk_client.upsert(doc_id3, doc)

    if "macos" in sg_platform:
        time.sleep(2)
        stdout = subprocess.check_output(command, shell=True)
        assert int(stdout) == 1 + log1_num, "did not find the expected match on sg info logs"
        stdout = subprocess.check_output(command1, shell=True)
        assert int(stdout) == 1 + log2_num, "did not find the expected match on sg info logs"
    else:
        _, stdout, _ = remote_executor.execute(command)
        assert int(stdout[0]) == 1 + log1_num, "did not find the expected match on sg info logs"
        _, stdout, _ = remote_executor.execute(command1)
        assert int(stdout[0]) == 1 + log2_num, "did not find the expected match on sg info log"

    sg_expvars = sg_client.get_expvars(url=sg_admin_url, auth=auth)
    non_mobile_ignore_count = sg_expvars["syncgateway"]["per_db"][sg_db]["cache"]["non_mobile_ignored_count"]
    assert non_mobile_ignore_count == 1, "non_mobile_ignore_count did not get expected count"

    # 8. Verify warn_count is 0
    if disable_persistent_config:
        assert sg_expvars["syncgateway"]["global"]["resource_utilization"]["warn_count"] == warn_count, "warn_count did not increment"
    else:
        assert sg_expvars["syncgateway"]["global"]["resource_utilization"]["warn_count"] == warn_count + 1, "warn_count did not match"
