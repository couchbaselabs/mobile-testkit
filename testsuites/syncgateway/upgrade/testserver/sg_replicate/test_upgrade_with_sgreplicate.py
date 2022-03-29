import os
import random
import time

from concurrent.futures import ProcessPoolExecutor
from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (SyncGateway)
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, replace_string_on_sgw_config, copy_sgconf_to_temp

from libraries.testkit.cluster import Cluster
from keywords import attachment
from CBLClient.Authenticator import Authenticator
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode, setup_sgreplicate1_on_sgconfig, setup_replications_on_sgconfig
# from utilities.cluster_config_utils import load_cluster_config_json, get_cluster, is_centralized_persistent_config_disabled, get_sg_version
from utilities.cluster_config_utils import load_cluster_config_json, get_cluster


def test_upgrade(params_from_base_test_setup, setup_customized_teardown_test):
    """
    @summary
        Test plan - Bottom of the page
        https://docs.google.com/spreadsheets/d/1k_tlz3zQSBCI1a9ZS0RDOH6pj3xVTalCoGytQwVqu-M/edit#gid=0
        This test case validates Sync Gateway server to be upgraded
        wihtout replication downtime along with couchbase lite clients
        [test prerequisites]:
        The conftest prepares the test environment,
        the initial (old) versions of SGW and CBS are provisioned at this point
        [test environment configuration]:
        The test environment setup includes: 2 CBS, 4SGW, and 2 SGW load balancer to balancer two sgw clusters
        The SGW load balancer is configured with nginx
        [test scenarios and steps]:
        1. Create user, session and docs on SG
        2. Starting continuous push_pull replication between TestServer(CBL DB1) and SGW cluster1 and also between Testserver(CBL DB2) and SGW cluster2
        3. Start sg-replicate1 replication for version 2.7.0 and below, otherwise set up sg-replicate2 replication on sgwconfig and deploy the configs
        4. Start a thread to keep updating docs on CBL
        5. option to test w/wo stopping replication before SGW upgrade
        6. Upgrade SGW one by one on cluster config list
        7. Restart SGWs with sg-replicate1 id and sg-replicate2 id
                by having same ids in order to continue upgrade of replications from sg-replicate-1 to sg-replicate2 if sgw version below 2.8.0
                otherwiser have only sg-replicate2 for 2.8.0 and above
        8. Once upgrade is completed, create new docs on sgw cluster1
        9. Create new replication with sg-replicate2
        10. Gather CBL docs new revs for verification
        11. Compare doc body and counts of one of the keys  of all docs on both SGW cluster1 SGW cluster2 are same
    """
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    cbs_ssl = params_from_base_test_setup["cbs_ssl"],
    sg_ssl = params_from_base_test_setup["sg_ssl"],
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"],
    use_views = params_from_base_test_setup["use_views"],
    number_replicas = params_from_base_test_setup["number_replicas"],
    delta_sync_enabled = params_from_base_test_setup["delta_sync_enabled"],
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"],
    upgraded_cbs_ssl = params_from_base_test_setup['upgraded_cbs_ssl']
    upgraded_sg_ssl = params_from_base_test_setup['upgraded_sg_ssl']
    upgraded_xattrs_enabled = params_from_base_test_setup['upgraded_xattrs_enabled']
    upgraded_use_views = params_from_base_test_setup['upgraded_use_views']
    upgraded_number_replicas = params_from_base_test_setup['upgraded_number_replicas']
    upgraded_delta_sync_enabled = params_from_base_test_setup['upgraded_delta_sync_enabled']
    upgraded_no_conflicts_enabled = params_from_base_test_setup['upgraded_no_conflicts_enabled']
    base_url = params_from_base_test_setup["base_url"]
    sg1_blip_url = params_from_base_test_setup["target1_url"]
    sg2_blip_url = params_from_base_test_setup["target2_url"]
    num_docs = int(params_from_base_test_setup['num_docs'])
    stop_replication_before_upgrade = params_from_base_test_setup['stop_replication_before_upgrade']
    sgw_cluster1_count = params_from_base_test_setup['sgw_cluster1_count']
    sgw_cluster2_count = params_from_base_test_setup['sgw_cluster2_count']
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    db = params_from_base_test_setup["db"]

    # update cluster_config with the post upgrade required params
    need_to_redeploy = False
    if (sg_ssl != upgraded_sg_ssl) and upgraded_sg_ssl:
        log_info("Enabling SSL on sync gateway after upgrade")
        need_to_redeploy = True
        persist_cluster_config_environment_prop(cluster_config, 'sync_gateway_ssl', True)

    if (cbs_ssl != upgraded_cbs_ssl) and upgraded_cbs_ssl:
        log_info("Running tests with cbs <-> sg ssl enabled after upgrade")
        # Enable ssl in cluster configs
        need_to_redeploy = True
        persist_cluster_config_environment_prop(cluster_config, 'cbs_ssl_enabled', True)

    if use_views != upgraded_use_views:
        need_to_redeploy = True
        if upgraded_use_views:
            log_info("Running SG tests using views after upgrade")
            # Enable sg views in cluster configs
            persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', True)
        else:
            log_info("Running tests not using views after upgrade")
            # Disable sg views in cluster configs
            persist_cluster_config_environment_prop(cluster_config, 'sg_use_views', False)

    if (number_replicas != upgraded_number_replicas) and int(upgraded_number_replicas) > 0:
        need_to_redeploy = True
        persist_cluster_config_environment_prop(cluster_config, 'number_replicas', upgraded_number_replicas)

    if sync_gateway_upgraded_version >= "2.0.0" and server_upgraded_version >= "5.0.0" and (xattrs_enabled != upgraded_xattrs_enabled):
        need_to_redeploy = True
        if upgraded_xattrs_enabled:
            log_info("Running test with xattrs for sync meta storage after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', True)
        else:
            log_info("Using document storage for sync meta data after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'xattrs_enabled', False)

        if upgraded_no_conflicts_enabled:
            log_info("Running with no conflicts after the upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', True)
        else:
            log_info("Running with conflicts after the upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'no_conflicts_enabled', False)

    if sync_gateway_upgraded_version >= "2.5.0" and server_upgraded_version >= "5.5.0" and (delta_sync_enabled != upgraded_delta_sync_enabled):
        need_to_redeploy = True
        if upgraded_delta_sync_enabled:
            log_info("Running with delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
        else:
            log_info("Running without delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    doc_obj = Document(base_url)
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    sg_user_channels = ["replication_1_channel", "replication_2_channel1", "replication_2_channel2", "replication_2_channel3", "replication_2_channel4"]
    replication1_channel = ["replication_1_channel"]
    replication2_channel1 = ["replication_2_channel1"]
    replication2_channel2 = ["replication_2_channel2"]
    replication2_channel3 = ["replication_2_channel3"]
    replication2_channel4 = ["replication_2_channel4"]
    sg1_user_name = "sg1_user"
    sg2_user_name = "sg2_user"
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    password = "password"
    sgw_cluster1_replication1 = "Mobile_Cluster1_Replication1"
    sgw_cluster1_replication1_att = "Mobile_att_Cluster1_Replication1"
    sgw_cluster2_replication1 = "SGW_Cluster2_Replication1"
    sgw_cluster1_replication1_ch1 = "SGW_Cluster1_ch1_Replication1"
    sgw_cluster1_replication1_ch2 = "SGW_Cluster1_ch2_Replication1"
    sgw_cluster1_replication1_ch3 = "SGW_Cluster1_ch3_Replication1"
    channel_list = [replication2_channel1, replication2_channel2, replication2_channel3]
    sgw_cluster1 = []
    sgw_cluster2 = []

    # 1. Create user, session and docs on SG
    sg_client = MobileRestClient()
    cluster = Cluster(config=cluster_config)
    sg_obj = SyncGateway()
    # Get actual sync gateway nodes from cluster configs
    json_cluster = load_cluster_config_json(cluster_config)

    # Replace string data-bucket on the sg config and redeploy on all 4 nodes.
    # This will set up 2 sgw nodes on one sgw cluster and 2 sgw nodes on second sgw cluster
    sg1_node = json_cluster["sync_gateways"][0]["ip"]
    sg2_node = json_cluster["sync_gateways"][1]["ip"]
    sg3_node = json_cluster["sync_gateways"][2]["ip"]
    sg4_node = json_cluster["sync_gateways"][3]["ip"]
    sg_node_list = [sg1_node, sg2_node, sg3_node, sg4_node]
    total_sgs_count = sgw_cluster1_count + sgw_cluster2_count
    count = 0

    sgw_cluster1.append(sg1_node)
    sgw_cluster1.append(sg2_node)
    sgw_cluster2.append(sg3_node)
    sgw_cluster2.append(sg4_node)
    sg1 = cluster.sync_gateways[0]
    sg3 = cluster.sync_gateways[2]
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sgw_cluster2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_conf_name, mode)
    sgw_cluster2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_sg_config)

    # 3. Start replications on SGW cluster1 to SGW cluster2. Will have 2 replications. One push replication and one pull replication

    sg_conf_name = 'sync_gateway_sg_replicate1_in_sgwconfig'
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    temp_sg_config_copy, _ = copy_sgconf_to_temp(sg_config, mode)
    if sync_gateway_version < "2.8.0":
        replication_1, sgw_repl1_id1 = setup_sgreplicate1_on_sgconfig(sg1.admin.admin_url, sg_db1, sg3.admin.admin_url, sg_db2, channels=replication1_channel, continuous=True)
        replication_2, sgw_repl1_id2 = setup_sgreplicate1_on_sgconfig(sg3.admin.admin_url, sg_db2, sg1.admin.admin_url, sg_db1, channels=replication1_channel, continuous=True)
    else:
        replication_1, sgw_repl1 = setup_replications_on_sgconfig(sg3.url, sg_db2, sg2_user_name, password, direction="push", channels=replication1_channel, continuous=True, replication_id=None)
        replication_2, sgw_repl2 = setup_replications_on_sgconfig(sg3.url, sg_db2, sg2_user_name, password, direction="pull", channels=replication1_channel, continuous=True, replication_id=None)
    replications_ids = "{},{}".format(replication_1, replication_2)
    replications_key = "replications"
    if sync_gateway_version < "2.8.0":
        replace_string = "\"{}\": {}{}{},".format(replications_key, "[", replications_ids, "]")
        temp_sg_config_with_sg1 = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sgreplicate2_replications }}", "")
        if sync_gateway_upgraded_version < "3.0.0":
            temp_sg_config = replace_string_on_sgw_config(temp_sg_config_with_sg1, "{{ replace_with_sg1_replications }}", replace_string)
        else:
            temp_sg_config = replace_string_on_sgw_config(temp_sg_config_with_sg1, "{{ replace_with_sg1_replications }}", "")
    else:
        replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replications_ids, "}")
        temp_sg_config_with_sg1 = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sg1_replications }}", "")
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config_with_sg1, "{{ replace_with_sgreplicate2_replications }}", replace_string)

    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), temp_sg_config)
    for node in sg_node_list:
        if count < sgw_cluster1_count:
            sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=node,
                                                sync_gateway_version=sync_gateway_version, enable_import=True)
        elif count < total_sgs_count:
            sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster2_config_path, url=node,
                                                sync_gateway_version=sync_gateway_version, enable_import=True)
        else:
            sg_obj.stop_sync_gateways(cluster_config=cluster_config, url=node)
        count += 1

    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster1_replication1_att, db=cbl_db1, channels=replication1_channel,
                        attachments_generator=attachment.generate_2_png_10_10)
    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster1_replication1, db=cbl_db1, channels=replication1_channel)
    limit_1 = num_docs * 2
    doc_ids = db.getDocIds(cbl_db1, limit=limit_1)
    sgw_cluster1_added_docs = db.getDocuments(cbl_db1, doc_ids)

    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster2_replication1, db=cbl_db2, channels=replication1_channel,
                        attachments_generator=attachment.generate_2_png_10_10)
    doc_ids2 = db.getDocIds(cbl_db2, limit=num_docs)
    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster1_replication1_ch1, db=cbl_db1, channels=replication2_channel1,
                        attachments_generator=attachment.generate_2_png_10_10)
    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster1_replication1_ch2, db=cbl_db1, channels=replication2_channel2,
                        attachments_generator=attachment.generate_2_png_10_10)
    db.create_bulk_docs(number=num_docs, id_prefix=sgw_cluster1_replication1_ch3, db=cbl_db1, channels=replication2_channel3,
                        attachments_generator=attachment.generate_2_png_10_10)
    # Starting continuous push_pull replication from TestServer to sync gateway cluster1
    log_info("Starting continuous push pull replication from TestServer to sync gateway")
    repl1, replicator_authenticator1, session1 = create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels,
                                                                                                sg1, sg1_user_name, sg_db1, cbl_db1, sg1_blip_url)

    repl2, _, _ = create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels,
                                                                 sg3, sg2_user_name, sg_db2, cbl_db2, sg2_blip_url)
    # Start 3rd replicator to verify docs with attachments gets replicated after the upgrade for one shot replications from sgw cluster1 to cbl db3
    repl_config3 = replicator.configure(cbl_db3, sg1_blip_url, continuous=False, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator1)
    repl3 = replicator.create(repl_config3)
    replicator.start(repl3)
    replicator.wait_until_replicator_idle(repl3)
    sg_client.add_docs(url=sg1.admin.admin_url, db=sg_db1, number=2, id_prefix="sgw_docs3", channels=replication2_channel4, generator="simple_user", attachments_generator=attachment.generate_2_png_10_10)
    terminator1_doc_id = 'terminator1'

    # Create sg replicate2 in sgw config by using same repl id of sg replicate1 for sg replicate2
    if sync_gateway_version < "2.8.0":
        if stop_replication_before_upgrade:
            sgw_replication1_id1 = None
            sgw_replication1_id2 = None
        else:
            sgw_replication1_id1 = sgw_repl1_id1
            sgw_replication1_id2 = sgw_repl1_id2
        replication_1, sgw_repl1 = setup_replications_on_sgconfig(sg3.url, sg_db2, sg2_user_name, password, direction="push", channels=replication1_channel, continuous=True, replication_id=sgw_replication1_id1)
        replication_2, sgw_repl2 = setup_replications_on_sgconfig(sg3.url, sg_db2, sg2_user_name, password, direction="pull", channels=replication1_channel, continuous=True, replication_id=sgw_replication1_id2)
        replications_ids = "{},{}".format(replication_1, replication_2)
        replications_key = "replications"
        sgr2_replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replications_ids, "}")
        temp_sg_config_copy, _ = copy_sgconf_to_temp(sg_config, mode)
        if sync_gateway_upgraded_version >= "3.0.0":
            temp_sg_config = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sg1_replications }}", "")
        if stop_replication_before_upgrade:
            sg1.stop_replication_by_id(sgw_repl1_id1, use_admin_url=True)
            sg1.stop_replication_by_id(sgw_repl1_id2, use_admin_url=True)
            temp_sg_config = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sg1_replications }}", "")
        else:
            temp_sg_config = replace_string_on_sgw_config(temp_sg_config_copy, "{{ replace_with_sg1_replications }}", replace_string)
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_sgreplicate2_replications }}", sgr2_replace_string)
        sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), temp_sg_config)
    # If no conflicts is not enabled then create conflicts on sgw cluster1 and sgw cluster2
    if not no_conflicts_enabled:
        sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session1)["rows"]
        for doc in sg_docs:
            if "sgw_cluster1_replication1" in doc:
                sg_client.add_conflict(url=sg1.url, db=sg_db1, doc_id=doc["id"], parent_revisions=doc["rev"],
                                       new_revision="2-foo", auth=session1)

    with ProcessPoolExecutor() as up:
        # Start updates in background process
        updates_future = up.submit(update_docs, db, cbl_db1, doc_ids,
                                   cbl_db2, doc_ids2, doc_obj, terminator1_doc_id)

        # 4. Upgrade SGW one by one on cluster config list
        cluster_util = ClusterKeywords(cluster_config)
        topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
        sync_gateways = topology["sync_gateways"]
        sgw_cluster1_list = sync_gateways[:2]
        sgw_cluster2_list = sync_gateways[2:]
        sg_obj.upgrade_sync_gateway(
            sgw_cluster1_list,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sgw_cluster1_config_path,
            cluster_config
        )

        sg_obj.upgrade_sync_gateway(
            sgw_cluster2_list,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sgw_cluster2_config_path,
            cluster_config
        )

        cluster = Cluster(config=cluster_config)

        if len(cluster.servers) < 1:
            raise Exception("Please provide at least 2 servers")

        server_urls = []
        for server in cluster.servers:
            server_urls.append(server.url)

        primary_server = cluster.servers[0]

        # 6. Restart SGWs after the sgw upgrade
        sg_obj = SyncGateway()
        # TODO : comment below and test
        """for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway after server upgrade {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)
            time.sleep(5)"""

        if need_to_redeploy:
            # Enable xattrs on all SG/SGAccel nodes
            # cc - Start 1 SG with import enabled, all with XATTRs enabled
            #    - Do not enable import in SG.
            if mode == "cc":
                enable_import = True
            sg_obj = SyncGateway()
            for sg in sgw_cluster1_list:
                sg_ip = host_for_url(sg["admin"])
                sg_obj.redeploy_sync_gateway_config(
                    cluster_config=cluster_config,
                    sg_conf=sgw_cluster1_config_path,
                    url=sg_ip,
                    sync_gateway_version=sync_gateway_upgraded_version,
                    enable_import=enable_import
                )

            for sg in sgw_cluster2_list:
                sg_ip = host_for_url(sg["admin"])
                sg_obj.redeploy_sync_gateway_config(
                    cluster_config=cluster_config,
                    sg_conf=sgw_cluster2_config_path,
                    url=sg_ip,
                    sync_gateway_version=sync_gateway_upgraded_version,
                    enable_import=enable_import
                )

        repl_config4 = replicator.configure(cbl_db3, sg1_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator1)
        repl4 = replicator.create(repl_config4)
        replicator.start(repl4)
        log_info("Trying to create terminator id ....")
        db.create_bulk_docs(number=1, id_prefix=terminator1_doc_id, db=cbl_db1, channels=replication2_channel4)
        log_info("Waiting for doc updates to complete")
        updated_doc_revs = updates_future.result()

        log_info("waiting for the replication to complete")
        replicator.wait_until_replicator_idle(repl4, max_times=3000)
        # set up another replicator to verify attachments replicated after the upgrade
        replicator.wait_until_replicator_idle(repl1, max_times=3000)
        replicator.wait_until_replicator_idle(repl2, max_times=3000)

        # 7. Gather CBL docs new revs for verification
        log_info("Gathering the updated revs for verification")
        doc_ids = []
        for doc_id in sgw_cluster1_added_docs:
            doc_ids.append(doc_id)
            if doc_id in updated_doc_revs:
                sgw_cluster1_added_docs[doc_id]["numOfUpdates"] = updated_doc_revs[doc_id]

        # 8. Compare rev id, doc body and revision history of all docs on both CBL and SGW
        verify_sg_docs_revision_history(sg1.admin.admin_url, sg_db=sg_db1, added_docs=sgw_cluster1_added_docs, terminator=terminator1_doc_id)

        # 9. If xattrs enabled, validate CBS contains _sync records for each doc
        if upgraded_xattrs_enabled:
            # Verify through SDK that there is no _sync property in the doc body
            bucket_name = 'data-bucket-1'
            sdk_client = get_cluster('couchbase://{}'.format(primary_server.host), bucket_name)
            log_info("Fetching docs from SDK")
            docs_from_sdk = sdk_client.get_multi(doc_ids)

            log_info("Verifying that there is no _sync property in the docs")
            for i in docs_from_sdk:
                if "_sync" in docs_from_sdk[i].content:
                    raise Exception("_sync section found in docs after upgrade")
    repl_id = [sgw_repl1, sgw_repl2]
    for channel in channel_list:
        replid = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg3.url,
            remote_db=sg_db2,
            remote_user=sg2_user_name,
            remote_password=password,
            channels=channel,
            continuous=True
        )
        repl_id.append(replid)
    replicator.wait_until_replicator_idle(repl1, max_times=3000)
    # Wait until all SGW replications are completed
    for replid in repl_id:
        sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, write_flag=True, max_times=3000)
    time.sleep(300)
    replicator.wait_until_replicator_idle(repl2, max_times=3000)
    limit_2 = num_docs * 10
    cbl_doc_ids2 = db.getDocIds(cbl_db2, limit=limit_2)  # number times 6 as it creates docs 6 times at 6 places
    # cbl_doc_ids2 = db.getDocIds(cbl_db2)  # number times 6 as it creates docs 6 times at 6 places
    print("cbl doc ids 2 are : ", cbl_doc_ids2)
    count = sum(sgw_cluster1_replication1 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication1 channel1 did not replicate to cbl db2"
    count = sum(sgw_cluster1_replication1_ch1 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel1 did not replicate to cbl db2"
    count = sum(sgw_cluster1_replication1_ch2 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel2 did not replicate to cbl db2"
    count = sum(sgw_cluster1_replication1_ch3 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel3 did not replicate to cbl db2"
    # Compare of sg1 docs to sg2docs(via CBL db2)
    sg_docs1 = sg_client.get_all_docs(url=sg1.admin.admin_url, db=sg_db1, include_docs=True)["rows"]

    for doc in sg_docs1:
        if "sgw_docs3" not in doc["id"] and "terminator1_0" not in doc["id"]:
            sg3_doc = sg_client.get_doc(url=sg3.admin.admin_url, db=sg_db2, doc_id=doc['doc']['_id'])
            if "numOfUpdates" in sg_docs1:
                assert doc["doc"]["numOfUpdates"] == sg3_doc["numOfUpdates"], "number of updates value is not same on both clusters for {}".format(doc)
            if sync_gateway_version < "2.8.0":
                assert doc["doc"]["_rev"] == sg3_doc["_rev"], "number of updates value is not same on both clusters for {}".format(doc)
    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


def verify_sg_docs_revision_history(url, sg_db, added_docs, terminator):
    sg_client = MobileRestClient()
    sg_docs = sg_client.get_all_docs(url=url, db=sg_db, include_docs=True)["rows"]
    expected_doc_map = {}
    for doc in added_docs:
        if "numOfUpdates" in added_docs[doc]:
            expected_doc_map[doc] = added_docs[doc]["numOfUpdates"] - 1
        else:
            expected_doc_map[doc] = 1
    for doc in sg_docs:
        if "sgw_docs" not in doc['id'] and "SGW_Cluster-1-Replication-1" in doc['id']:
            key = doc["doc"]["_id"]
            if terminator in key:
                continue
            rev = doc["doc"]["_rev"]
            rev_gen = int(rev.split("-")[0])

            try:
                del doc["doc"]["_rev"]
            except KeyError:
                log_info("no _rev exists in the dict")

            del doc["doc"]["_id"]
            try:
                del added_docs[key]["_id"]
            except KeyError:
                log_info("Ignoring id verification")
            assert rev_gen == expected_doc_map[key], "revision mismatch"
            assert len(doc["doc"]) == len(added_docs[key]), "doc length mismatch"

    log_info("finished verify_sg_docs_revision_history.")


def send_changes_termination_doc(db, cbl_db, terminator_doc_id, terminator_channel):
    db.create_bulk_docs(number=1, id_prefix=terminator_doc_id, db=cbl_db, channels=terminator_channel)


def update_docs(db, cbl_db1, cbl_db1_doc_ids, cbl_db2, cbl_db2_doc_ids, doc_obj, terminator_doc_id_prefix):
    log_info("Starting doc updates")
    docs_per_update = 3
    doc_revs = {}
    terminator_doc_id = "{}_0".format(terminator_doc_id_prefix)
    terminator_not_found_msg = "Termination doc not found"

    while True:
        log_info("randomly update docs waiting for terminator arrive...")
        try:
            term_doc = db.getDocument(cbl_db1, terminator_doc_id)
            if term_doc == -1:
                log_info(terminator_not_found_msg)
            else:
                doc_type = term_doc.__class__.__name__
                if doc_type == "MemoryPointer":
                    log_info("update_docs: Found termination doc")
                    # return
                    log_info("update_docs: Updated {} docs".format(len(doc_revs)))
                    return doc_revs
                else:
                    log_info("update_docs: doc object is retrieved correctly")
        except Exception:
            log_info(terminator_not_found_msg)

        cbl_db_docs_to_update = update_random_docs(docs_per_update, cbl_db1_doc_ids, db, cbl_db1, doc_obj)
        update_random_docs(docs_per_update, cbl_db2_doc_ids, db, cbl_db2, doc_obj)

        for doc_id, doc_body in list(cbl_db_docs_to_update.items()):
            new_doc = db.getDocument(cbl_db1, doc_id)
            doc_revs[doc_id] = doc_obj.toMap(new_doc)['numOfUpdates']

        time.sleep(5)


def update_random_docs(docs_per_update, cbl_doc_ids, db, cbl_db, doc_obj):
    random_doc_ids_list = []
    for _ in range(docs_per_update):
        random_doc_id = random.choice(cbl_doc_ids)
        random_doc_ids_list.append(random_doc_id)

    cbl_db_docs_to_update = {}
    for doc_id in random_doc_ids_list:
        log_info("Updating doc_id: {}".format(doc_id))
        doc_body = doc_obj.toMap(db.getDocument(cbl_db, doc_id))
        # numOfUpdates counts how many updates are made to the current document
        # starting index value from 2, 2 means numOfUpdates = 0, and 3 means numOfUpdates = 1
        # the current framework take 0 as False and 1 as True, even though an integer type is expected
        # this is temporary solution to avoid this issue
        if "numOfUpdates" in doc_body:
            doc_body["numOfUpdates"] += 1
        else:
            doc_body["numOfUpdates"] = 2
        cbl_db_docs_to_update[doc_id] = doc_body
        db.updateDocument(database=cbl_db, doc_id=doc_id, data=doc_body)

    return cbl_db_docs_to_update


def create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels, sg, sg_user_name, sg_db, cbl_db, sg_blip_url):

    sg_user_password = "password"
    sg_client.create_user(url=sg.admin.admin_url, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels)
    sg_cookie, sg_session = sg_client.create_session(url=sg.admin.admin_url, db=sg_db, name=sg_user_name)
    session = sg_cookie, sg_session

    replicator_authenticator = authenticator.authentication(sg_session, sg_cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    return repl, replicator_authenticator, session
