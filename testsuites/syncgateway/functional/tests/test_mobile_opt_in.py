
import pytest
from requests.exceptions import HTTPError
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway
from keywords.userinfo import UserInfo
from keywords.utils import host_for_url, log_info
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import get_cluster
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
    doc = document.create_doc(doc_id=doc_id1, channels=['mobileOptIn'], prop_generator=update_mobile_prop, non_sgw=True)
    sdk_client.upsert(doc_id1, doc)
    sg_get_doc1 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id1, auth=test_auth_session)
    assert sg_get_doc1['_rev'].startswith('1-') and sg_get_doc1['_id'] == doc_id1
    # Additional coverage for case #1
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id1, number_updates=1, auth=test_auth_session)
    sg_get_doc1 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id1, auth=test_auth_session)
    assert sg_get_doc1['_rev'].startswith('2-') and sg_get_doc1['_id'] == doc_id1

    # Create second doc via SDK with type non mobile. Case #2
    doc_id2 = 'mobile_opt_out_sdk_doc'
    doc = document.create_doc(doc_id=doc_id2, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop, non_sgw=True)
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
    doc3 = sdk_client.get(doc_id3)
    doc_body = doc3.content
    doc_body["updated_sdk_via_sg"] = "1"
    sdk_client.upsert(doc_id3, doc_body)
    sg_get_doc3 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id3, auth=test_auth_session)
    assert sg_get_doc3['_rev'].startswith('2-') and sg_get_doc3['_id'] == doc_id3
    log_info("sg get doc3 is {}".format(sg_get_doc3))

    # Create fourth sg doc with mobile opt out and update via sdk. Case #4 and case #8
    doc_id4 = 'mobile_opt_out_sg_doc'
    doc_body = document.create_doc(doc_id=doc_id4, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    # update vis SDK
    sg_get_doc4 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id4, auth=test_auth_session)
    doc4 = sdk_client.get(doc_id4)
    doc_body4 = doc4.content
    rev = sg_get_doc4['_rev']
    doc_body4["updated_sdk_via_sg"] = "1"
    sdk_client.upsert(doc_id4, doc_body4)
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
    doc = document.create_doc(doc_id=doc_id5, channels=['mobileOptIn'], prop_generator=update_mobile_prop, non_sgw=True)
    sdk_client.upsert(doc_id5, doc)
    sg_get_doc5 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id5, auth=test_auth_session)
    log_info("sg get doc 5 is {}".format(sg_get_doc5))
    assert sg_get_doc5['_rev'].startswith('1-') and sg_get_doc5['_id'] == doc_id5

    # Create sixth sg doc with mobile opt out  and update via sdk with opt in
    doc_id6 = 'mobileoptout_sg_doc_sdkupdate_optin'
    doc_body = document.create_doc(doc_id=doc_id6, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    sdk_get_doc6 = sdk_client.get(doc_id4)
    doc_body6 = sdk_get_doc6.content
    doc_body6["type"] = "mobile"
    sdk_client.upsert(doc_id6, doc_body6)
    sg_get_doc6 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id6, auth=test_auth_session)
    assert sg_get_doc6['_rev'].startswith('2-') and sg_get_doc6['_id'] == doc_id6

    # Create seventh sg doc with mobile opt in  and update via sdk with opt out
    doc_id7 = 'mobileoptin_sg_doc_sdkupdate_optout'
    doc_body = document.create_doc(doc_id=doc_id7, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    sdk_get_doc7 = sdk_client.get(doc_id4)
    doc_body7 = sdk_get_doc7.content
    doc_body7["type"] = "mobile opt out"
    sdk_client.upsert(doc_id7, doc_body7)
    with pytest.raises(HTTPError) as he:
        sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id7, auth=test_auth_session)
    log_info(he.value)
    resp = str(he.value)
    assert resp.startswith('404 Client Error: Not Found for url:')

    # Create eighth sdk doc with import disabled and add mobile property and update via sg. Case #7
    sg_conf_name = "xattrs/mobile_opt_in_no_import"
    sg_no_import_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_util = SyncGateway()
    sg_util.start_sync_gateways(cluster_config=cluster_conf, url=sg_url, config=sg_no_import_conf)

    doc_id8 = 'mobile_opt_in_sg_rewrite_with_importdisabled'
    sdk_doc_body = document.create_doc(doc_id=doc_id8, channels=['mobileOptIn'], prop_generator=update_mobile_prop, non_sgw=True)
    sdk_client.upsert(doc_id8, sdk_doc_body)
    sg_doc_body = document.create_doc(doc_id=doc_id8, channels=['mobileOptIn'], prop_generator=update_mobile_prop)
    with pytest.raises(HTTPError) as he:
        sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=test_auth_session)
    log_info(he.value)
    assert str(he.value).startswith('409 Client Error: Conflict for url:')
    sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id8, number_updates=1, auth=test_auth_session)
    sg_get_doc8 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id8, auth=test_auth_session)
    assert sg_get_doc8['_rev'].startswith('2-') and sg_get_doc8['_id'] == doc_id8

    # Create ninth sdk doc with import disabled and add mobile property and update via sg. Case #8
    doc_id9 = 'mobile_opt_out_sg_rewrite_with_importdisabled'
    sdk_doc_body9 = document.create_doc(doc_id=doc_id9, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop, non_sgw=True)
    sdk_client.upsert(doc_id9, sdk_doc_body9)
    sg_doc_body9 = document.create_doc(doc_id=doc_id9, channels=['mobileOptIn'], prop_generator=update_non_mobile_prop)
    sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body9, auth=test_auth_session)
    sg_get_doc9 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id9, auth=test_auth_session)
    assert sg_get_doc9['_rev'].startswith('1-') and sg_get_doc9['_id'] == doc_id9
