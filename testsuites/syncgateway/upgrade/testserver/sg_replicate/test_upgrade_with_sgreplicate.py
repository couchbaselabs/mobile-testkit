import os
import random
import time

from concurrent.futures import ProcessPoolExecutor
from couchbase.bucket import Bucket

from keywords.couchbaseserver import verify_server_version
from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (verify_sync_gateway_version,
                                  verify_sync_gateway_product_info,
                                  SyncGateway)
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import SDK_TIMEOUT
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, replace_string_on_sgw_config, copy_sgconf_to_temp

from libraries.testkit.cluster import Cluster
from keywords import attachment
from CBLClient.Authenticator import Authenticator
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode
# from libraries.provision.install_nginx import install_nginx_for_2_sgw_clusters
from utilities.cluster_config_utils import load_cluster_config_json
from keywords.utils import compare_docs


def test_upgrade(params_from_base_test_setup, setup_customized_teardown_test):
    """
    @summary
        This test case validates Sync Gateway server to be upgraded
        wihtout replication downtime along with couchbase lite clients
        [test prerequisites]:
        The conftest prepares the test environment,
        the initial (old) versions of SGW and CBS are provisioned at this point
        [test environment configuration]:
        The test environment setup includes: 2 CBS, 2SGW, and 1 SGW load balancer
        The SGW load balancer is configured with nginx
        [test scenarios and steps]:
        1. Create user, session and docs on SG
        2. Starting continuous push_pull replication between TestServer and SGW
        3. Start a thread to keep updating docs on CBL
        4. Upgrade SGW one by one on cluster config list
        5. Upgrade CBS one by one on cluster config list
        6. Restart SGWs after the server upgrade
        7. Gather CBL docs new revs for verification
        8. Compare rev id, doc body and revision history of all docs on both CBL and SGW
        9. If xattrs enabled, validate CBS contains _sync records for each doc
    """
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    server_version = params_from_base_test_setup['server_version']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    cbs_ssl = params_from_base_test_setup["cbs_ssl"],
    sg_ssl = params_from_base_test_setup["sg_ssl"],
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"],
    use_views = params_from_base_test_setup["use_views"],
    number_replicas = params_from_base_test_setup["number_replicas"],
    delta_sync_enabled = params_from_base_test_setup["delta_sync_enabled"],
    upgraded_cbs_ssl = params_from_base_test_setup['upgraded_cbs_ssl']
    upgraded_sg_ssl = params_from_base_test_setup['upgraded_sg_ssl']
    upgraded_xattrs_enabled = params_from_base_test_setup['upgraded_xattrs_enabled']
    upgraded_use_views = params_from_base_test_setup['upgraded_use_views']
    upgraded_number_replicas = params_from_base_test_setup['upgraded_number_replicas']
    upgraded_delta_sync_enabled = params_from_base_test_setup['upgraded_delta_sync_enabled']
    base_url = params_from_base_test_setup["base_url"]
    sg1_blip_url = params_from_base_test_setup["target1_url"]
    sg2_blip_url = params_from_base_test_setup["target2_url"]
    num_docs = int(params_from_base_test_setup['num_docs'])
    cbs_platform = params_from_base_test_setup['cbs_platform']
    cbs_toy_build = params_from_base_test_setup['cbs_toy_build']
    stop_replication_before_upgrade = params_from_base_test_setup['stop_replication_before_upgrade']
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    db = params_from_base_test_setup["db"]
    # sg_config = params_from_base_test_setup["sg_config"]
    # sg1_admin_url = params_from_base_test_setup["sg_admin_url"]
    # sg_ip = params_from_base_test_setup["sg_ip"]


    # sg_conf_name = 'listener_tests/multiple_sync_gateways'
   # sg_config = sync_gateway_config_path_for_mode(sg_conf_name, mode)

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

    if sync_gateway_upgraded_version >= "2.5.0" and server_upgraded_version >= "5.5.0" and (delta_sync_enabled != upgraded_delta_sync_enabled):
        # need_to_redeploy = True
        if upgraded_delta_sync_enabled:
            log_info("Running with delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
        else:
            log_info("Running without delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    doc_obj = Document(base_url)
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    sg_user_channels = ["replication_1_channel", "replication_2_channel1", "replication_2_channel2", "replication_2_channel3"]
    replication1_channel = ["replication_1_channel"]
    replication2_channel1 = ["replication_2_channel1"]
    replication2_channel2 = ["replication_2_channel2"]
    replication2_channel3 = ["replication_2_channel3"]
    sg1_user_name = "sg1_user"
    sg2_user_name = "sg2_user"
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    password = "password"
    SGW_Cluster1_Replication1 = "SGW_Cluster1_Replication1"
    SGW_Cluster2_Replication1 = "SGW_Cluster2_Replication1"
    SGW_Cluster1_Replication1_ch1 = "SGW_Cluster1_ch1_Replication1"
    SGW_Cluster1_Replication1_ch2 = "SGW_Cluster1_ch2_Replication1"
    SGW_Cluster1_Replication1_ch3 = "SGW_Cluster1_ch3_Replication1"
    channel_list = [replication2_channel1, replication2_channel2, replication2_channel3]
    sgw_cluster1 = []
    sgw_cluster2 = []
    # 1. Create user, session and docs on SG
    sg_client = MobileRestClient()
    cluster = Cluster(config=cluster_config)
    sg_obj = SyncGateway()
    # Get actual sync gateway nodes from cluster configs
    json_cluster = load_cluster_config_json(cluster_config)
    
    # cluster.reset(sg_config_path=sg_config)

    # Replace string data-bucket on the sg config and redeploy on all 4 nodes. 
    # This will set up 2 sgw nodes on one sgw cluster and 2 sgw nodes on second sgw cluster
    sg1_node = json_cluster["sync_gateways"][0]["ip"]
    sg2_node = json_cluster["sync_gateways"][1]["ip"]
    sg3_node = json_cluster["sync_gateways"][2]["ip"]
    sg4_node = json_cluster["sync_gateways"][3]["ip"]
    sgw_cluster1.append(sg1_node)
    sgw_cluster1.append(sg2_node)
    sgw_cluster2.append(sg3_node)
    sgw_cluster2.append(sg4_node)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]
    sg3 = cluster.sync_gateways[2]
    sg4 = cluster.sync_gateways[3]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sgw_cluster1_repl2_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_conf_name, mode)
    sgw_cluster2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_conf_name, mode)
    sgw_cluster2_repl2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_repl2_conf_name, mode)
    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)
    sgw_cluster1_repl2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_repl2_sg_config)
    sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg1_node,
                                        sync_gateway_version=sync_gateway_version, enable_import=True)
    sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg2_node,
                                        sync_gateway_version=sync_gateway_version, enable_import=True)
                
    sgw_cluster2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_sg_config)
    sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster2_config_path, url=sg3_node,
                                        sync_gateway_version=sync_gateway_version, enable_import=True)
    sg_obj.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster2_config_path, url=sg4_node,
                                        sync_gateway_version=sync_gateway_version, enable_import=True)

    # 3. Start replications on SGW cluster1 to SGW cluster2. Will have 2 replications. One push replication and one pull replication
    sg1.start_push_replication(
        sg3.admin.admin_url,
        sg_db1,
        sg_db2,
        continuous=True,
        channels=replication1_channel,
        use_admin_url=True
    )
    sg1.start_pull_replication(
        sg3.admin.admin_url,
        sg_db2,
        sg_db1,
        continuous=True,
        use_remote_target=True,
        channels=replication1_channel,
        use_admin_url=True
    )

    num_docs = 10
    db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster1_Replication1, db=cbl_db1, channels=replication1_channel,
                        attachments_generator=attachment.generate_2_png_10_10)
    doc_ids = db.getDocIds(cbl_db1, limit=num_docs)
    sgw_cluster1_added_docs = db.getDocuments(cbl_db1, doc_ids)
    log_info("Added {} docs".format(len(doc_ids)))

    db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster2_Replication1, db=cbl_db2, channels=replication1_channel,
                        attachments_generator=attachment.generate_2_png_10_10)
    doc_ids2 = db.getDocIds(cbl_db2, limit=num_docs)
    # sgw_cluster2_added_docs = db.getDocuments(cbl_db2, doc_ids)
    log_info("Added {} docs".format(len(doc_ids2)))

    db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster1_Replication1_ch1, db=cbl_db1, channels=replication2_channel1,
                        attachments_generator=attachment.generate_2_png_10_10)
    db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster1_Replication1_ch2, db=cbl_db1, channels=replication2_channel2,
                        attachments_generator=attachment.generate_2_png_10_10)
    db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster1_Replication1_ch3, db=cbl_db1, channels=replication2_channel3,
                        attachments_generator=attachment.generate_2_png_10_10)
    # Starting continuous push_pull replication from TestServer to sync gateway cluster1
    log_info("Starting continuous push pull replication from TestServer to sync gateway")
    print("sg1.ip is ", sg1.ip)
    print("sg3.ip is ", sg3.ip)
    repl1, replicator_authenticator1 = create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels,
                                                                                      sg1, sg1_user_name, sg_db1, cbl_db1, sg1_blip_url)

    repl2, _ = create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels,
                                                              sg3, sg2_user_name, sg_db2, cbl_db2, sg2_blip_url)
    # Start 3rd replicator to verify docs with attachments gets replicated after the upgrade for one shot replications from sgw cluster1 to cbl db3
    repl_config3 = replicator.configure(cbl_db3, sg1_blip_url, continuous=False, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator1)
    repl3 = replicator.create(repl_config3)
    replicator.start(repl3)
    replicator.wait_until_replicator_idle(repl3)
    # repl3 = create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels,
    #                                                       sg1, sg1_user_name, sg_db1, cbl_db3, sg1_blip_url)
    sg_client.add_docs(url=sg1.admin.admin_url, db=sg_db1, number=2, id_prefix="sgw_docs3", channels=sg_user_channels, generator="simple_user", attachments_generator=attachment.generate_2_png_10_10)
    terminator1_doc_id = 'terminator1'

    if stop_replication_before_upgrade:
        active_tasks = sg1.admin.get_active_tasks()
        replication_id1 = active_tasks[0]["replication_id"]
        print("replicaation id1 is ", replication_id1)
        # replication_id2 = active_tasks[1]["replication_id"]
        # SGW_Cluster1_Replication1_restart_upgrade = "SGW_Cluster1_Replication1_restart_upgrade"
        sg1.stop_replication_by_id(replication_id1, use_admin_url=True)
        # sg1.stop_replication_by_id(replication_id2, use_admin_url=True)
        # db.create_bulk_docs(number=num_docs, id_prefix=SGW_Cluster1_Replication1_restart_upgrade, db=cbl_db1, channels=replication1_channel,
        #                     attachments_generator=attachment.generate_2_png_10_10)

    with ProcessPoolExecutor() as up:
        # Start updates in background process
        updates_future = up.submit(update_docs, db, cbl_db1, doc_ids,
                                   cbl_db2, doc_ids2, doc_obj, terminator1_doc_id)
        # updates_future2 = up.submit(update_docs, db, cbl_db2, sgw_cluster2_added_docs,
        #                             doc_obj, terminator2_doc_id)

        # 4. Upgrade SGW one by one on cluster config list
        cluster_util = ClusterKeywords(cluster_config)
        time.sleep(60)
        topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
        sync_gateways = topology["sync_gateways"]
        sgw_cluster1_list = sync_gateways[:2]
        sgw_cluster2_list = sync_gateways[2:]
        print("upgrading SGWS cluster1 ....")
        print("SGW clust list 1 is ,", sgw_cluster1_list)
        print("SGW clust list is ,", sgw_cluster2_list)

        upgrade_sync_gateway(
            sgw_cluster1_list,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sgw_cluster1_repl2_config_path,
            cluster_config
        )

        print("upgrading SGWS cluster2 ....")
        upgrade_sync_gateway(
            sgw_cluster2_list,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sgw_cluster2_config_path,
            cluster_config
        )
        
        # 5. Upgrade CBS one by one on cluster config list
        cluster = Cluster(config=cluster_config)

        if len(cluster.servers) < 2:
            raise Exception("Please provide at least 3 servers")

        server_urls = []
        for server in cluster.servers:
            server_urls.append(server.url)

        primary_server = cluster.servers[0]
        secondary_server = cluster.servers[1]
        servers = cluster.servers[1:]
        ### TODO: Enable after getting upgrade test work
        """upgrade_server_cluster(
            servers,
            primary_server,
            secondary_server,
            server_version,
            server_upgraded_version,
            server_urls,
            cluster_config,
            cbs_platform,
            toy_build=cbs_toy_build
        )"""

        # 6. Restart SGWs after the server upgrade
        sg_obj = SyncGateway()
        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway after server upgrade {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)
            time.sleep(5)

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
                # Check Import showing up on all nodes

        repl_config4 = replicator.configure(cbl_db3, sg1_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator1)
        repl4 = replicator.create(repl_config4)
        replicator.start(repl4)
        # log_info("waiting for the replication to complete")
        # replicator.wait_until_replicator_idle(repl4, max_times=3000)
        log_info("Trying to create terminator id ....")
        db.create_bulk_docs(number=1, id_prefix=terminator1_doc_id, db=cbl_db1, channels=sg_user_channels)
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
        # TODO : Enable it once upgrade test done ## verify_sg_docs_revision_history(sg1.admin.admin_url, db, cbl_db3, num_docs + 3, sg_db=sg_db1, added_docs=sgw_cluster1_added_docs, terminator=terminator1_doc_id)

        # 9. If xattrs enabled, validate CBS contains _sync records for each doc
        if upgraded_xattrs_enabled:
            # Verify through SDK that there is no _sync property in the doc body
            bucket_name = 'data-bucket-1'
            sdk_client = Bucket('couchbase://{}/{}'.format(primary_server.host, bucket_name), password='password', timeout=SDK_TIMEOUT)
            log_info("Fetching docs from SDK")
            docs_from_sdk = sdk_client.get_multi(doc_ids)

            log_info("Verifying that there is no _sync property in the docs")
            for i in docs_from_sdk:
                if "_sync" in docs_from_sdk[i].value:
                    raise Exception("_sync section found in docs after upgrade")
    repl_id = []
    for channel in channel_list:
        print("starting SGW replication 1 for channel -----", channel)
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
        """print("starting SGW replication 2..... ")
        sgw_repl_2 = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg3.url,
            remote_db=sg_db2,
            remote_user=sg2_user_name,
            remote_password=password,
            channels=replication2_channel2,
            continuous=True
        )
        print("starting SGW replication 3---- ")
        sgw_repl_3 = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg3.url,
            remote_db=sg_db2,
            remote_user=sg2_user_name,
            remote_password=password,
            channels=replication2_channel3,
            continuous=True
        )"""
    print(sg1.admin.get_sgreplicate2_active_tasks(sg_db1))
    replicator.wait_until_replicator_idle(repl1, max_times=3000)
    # Wait until all SGW replications are completed
    for replid in repl_id:
        sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, num_of_expected_written_docs=num_docs, max_times=25) # TODO: change max_times once reads and write bug fixed
        #sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl_2, num_of_expected_read_docs=num_docs, num_of_expected_written_docs=num_docs, max_times=25) # TODO: change max_times once reads and write bug fixed
        #sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl_3, num_of_expected_read_docs=num_docs, num_of_expected_written_docs=num_docs, max_times=25) # TODO: change max_times once reads and write bug fixed

    if stop_replication_before_upgrade:
        sgw_repl_upgrade_id = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg3.url,
            remote_db=sg_db2,
            remote_user=sg2_user_name,
            remote_password=password,
            channels=replication1_channel,
            continuous=True
        )
        sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl_upgrade_id, num_of_expected_written_docs=num_docs, max_times=25) # TODO: change max_times once reads and write bug fixed
    replicator.wait_until_replicator_idle(repl2, max_times=3000)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    # if stop_replication_before_upgrade:
    #     count = sum(SGW_Cluster1_Replication1_restart_upgrade in s for s in cbl_doc_ids2)
    #    assert count == num_docs, "all docs with replication1 before upgrade did not replicate to cbl db2"
    count = sum(SGW_Cluster1_Replication1 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication1 channel1 did not replicate to cbl db2"
    count = sum(SGW_Cluster1_Replication1_ch1 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel1 did not replicate to cbl db2"
    count = sum(SGW_Cluster1_Replication1_ch2 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel2 did not replicate to cbl db2"
    count = sum(SGW_Cluster1_Replication1_ch3 in s for s in cbl_doc_ids2)
    assert count == num_docs, "all docs with replication2 channel3 did not replicate to cbl db2"
    # Compare of sg1 docs to sg2docs(via CBL db2)
    sg_docs = sg_client.get_all_docs(url=sg1.admin.admin_url, db=sg_db1, include_docs=True)["rows"]
    doc_ids = db.getDocIds(cbl_db2)
    cbl_db_docs2 = db.getDocuments(cbl_db2, doc_ids)
    compare_docs(cbl_db2, db, sg_docs)
    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


def verify_sg_docs_revision_history(url, db, cbl_db3, num_docs, sg_db, added_docs, terminator):
    sg_client = MobileRestClient()
    sg_docs = sg_client.get_all_docs(url=url, db=sg_db, include_docs=True)["rows"]
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    print("cbl doc ids 3 are ...", cbl_doc_ids3)
    cbl_docs3 = db.getDocuments(cbl_db3, cbl_doc_ids3)
    num_sg_docs_in_cbldb3 = 0
    expected_doc_map = {}
    for doc in added_docs:
        if "numOfUpdates" in added_docs[doc]:
            expected_doc_map[doc] = added_docs[doc]["numOfUpdates"] - 1
        else:
            expected_doc_map[doc] = 1
    for doc in cbl_docs3:
        if "sgw_docs" in doc:
            num_sg_docs_in_cbldb3 += 1
            assert '_attachments' in cbl_docs3[doc], "_attachments does not exist in doc created in sgw"
    assert num_sg_docs_in_cbldb3 == 2, "sgw docs are not replicated to cbl db2"
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
    """cbl_db1_doc_ids = []
    cbl_db2_doc_ids = []
    for doc in added_docs1:
        cbl_db1_doc_ids.append(doc)

    for doc in added_docs2:
        cbl_db2_doc_ids.append(doc)"""

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

        #update_random_docs(docs_per_update, cbl_db1_doc_ids, db, cbl_db1, doc_obj)
        print("updating 2nd cluster now")
        #update_random_docs(docs_per_update, cbl_db2_doc_ids, db, cbl_db2, doc_obj)

        random_doc_ids_list1 = []
        random_doc_ids_list2 = []
        print("cbl doc ids list1,", cbl_db1_doc_ids)
        print("cbl doc ids list2,", cbl_db2_doc_ids)
        for _ in range(docs_per_update):
            random_doc_id = random.choice(cbl_db1_doc_ids)
            random_doc_ids_list1.append(random_doc_id)
        for _ in range(0, docs_per_update):
            random_doc_id = random.choice(cbl_db2_doc_ids)
            random_doc_ids_list2.append(random_doc_id)

        cbl_db_docs_to_update = {}
        cbl_db_docs_to_update1 = {}
        print("random doc ids list1,", random_doc_ids_list1)
        print("random doc ids list2,", random_doc_ids_list2)
        for doc_id in random_doc_ids_list1:
            log_info("Updating doc_id: sgw cluster1 {}".format(doc_id))
            doc_body = doc_obj.toMap(db.getDocument(cbl_db1, doc_id))
            # numOfUpdates counts how many updates are made to the current document
            # starting index value from 2, 2 means numOfUpdates = 0, and 3 means numOfUpdates = 1
            # the current framework take 0 as False and 1 as True, even though an integer type is expected
            # this is temporary solution to avoid this issue
            if "numOfUpdates" in doc_body:
                doc_body["numOfUpdates"] += 1
            else:
                doc_body["numOfUpdates"] = 2 + 1
            cbl_db_docs_to_update[doc_id] = doc_body
            db.updateDocument(database=cbl_db1, doc_id=doc_id, data=doc_body)

        for doc_id in random_doc_ids_list2:
            log_info("Updating doc_id: sgw cluster2 {}".format(doc_id))
            doc_body = doc_obj.toMap(db.getDocument(cbl_db2, doc_id))
            # numOfUpdates counts how many updates are made to the current document
            # starting index value from 2, 2 means numOfUpdates = 0, and 3 means numOfUpdates = 1
            # the current framework take 0 as False and 1 as True, even though an integer type is expected
            # this is temporary solution to avoid this issue
            if "numOfUpdates" in doc_body:
                doc_body["numOfUpdates"] += 1
            else:
                doc_body["numOfUpdates"] = 2 + 1
            cbl_db_docs_to_update1[doc_id] = doc_body
            db.updateDocument(database=cbl_db2, doc_id=doc_id, data=doc_body)

        for doc_id, doc_body in list(cbl_db_docs_to_update.items()):
            new_doc = db.getDocument(cbl_db1, doc_id)
            doc_revs[doc_id] = doc_obj.toMap(new_doc)['numOfUpdates']

        time.sleep(5)


def update_random_docs(docs_per_update, cbl_doc_ids, db, cbl_db, doc_obj):
    random_doc_ids_list = []
    for _ in range(docs_per_update):
            random_doc_id = random.choice(cbl_doc_ids)
            random_doc_ids_list.append(random_doc_id)

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
                doc_body["numOfUpdates"] = 2 + 1
            # cbl_db_docs_to_update[doc_id] = doc_body
            db.updateDocument(database=cbl_db, doc_id=doc_id, data=doc_body)


def upgrade_server_cluster(servers, primary_server, secondary_server, server_version, server_upgraded_version, server_urls, cluster_config, cbs_platform, toy_build=None):
    log_info('------------------------------------------')
    log_info('START server cluster upgrade')
    log_info('------------------------------------------')
    # Upgrade all servers except the primary server
    for server in servers:
        log_info("Checking for the server version: {}".format(server_version))
        verify_server_version(server.host, server_version)
        log_info("Rebalance out server: {}".format(server.host))
        primary_server.rebalance_out(server_urls, server)
        log_info("Upgrading the server: {}".format(server.host))
        primary_server.upgrade_server(cluster_config=cluster_config, server_version_build=server_upgraded_version, target=server.host, cbs_platform=cbs_platform, toy_build=toy_build)
        log_info("Adding the node back to the cluster: {}".format(server.host))
        primary_server.add_node(server)
        log_info("Rebalance in server: {}".format(server.host))
        primary_server.rebalance_in(server_urls, server)
        log_info("Checking for the server version after the rebalance : {}".format(server_upgraded_version))
        verify_server_version(server.host, server_upgraded_version)
        time.sleep(10)

    # Upgrade the primary server
    primary_server_services = "kv,index,n1ql"
    log_info("Checking for the primary server version: {}".format(server_version))
    verify_server_version(primary_server.host, server_version)
    log_info("Rebalance out primary server: {}".format(primary_server.host))
    secondary_server.rebalance_out(server_urls, primary_server)
    log_info("Upgrading the primary server: {}".format(primary_server.host))
    secondary_server.upgrade_server(cluster_config=cluster_config, server_version_build=server_upgraded_version, target=primary_server.host, cbs_platform=cbs_platform, toy_build=toy_build)
    log_info("Adding the node back to the cluster for primary server: {}".format(primary_server.host))
    secondary_server.add_node(primary_server, services=primary_server_services)
    log_info("Rebalance in primary server: {}".format(primary_server.host))
    secondary_server.rebalance_in(server_urls, primary_server)
    log_info("Checking for the primary server version after the rebalance: {}".format(server_upgraded_version))
    verify_server_version(primary_server.host, server_upgraded_version)
    log_info("Upgraded all the server nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END server cluster upgrade')
    log_info('------------------------------------------')


def upgrade_sync_gateway(sync_gateways, sync_gateway_version, sync_gateway_upgraded_version, sg_conf, cluster_config):
    log_info('------------------------------------------')
    log_info('START Sync Gateway cluster upgrade')
    log_info('------------------------------------------')

    sg_obj = SyncGateway()

    for sg in sync_gateways:
        sg_ip = host_for_url(sg["admin"])
        log_info("Checking for sync gateway product info before upgrade")
        verify_sync_gateway_product_info(sg_ip)
        log_info("Checking for sync gateway version: {}".format(sync_gateway_version))
        verify_sync_gateway_version(sg_ip, sync_gateway_version)
        log_info("Upgrading sync gateway: {}".format(sg_ip))
        sg_obj.upgrade_sync_gateways(
            cluster_config=cluster_config,
            sg_conf=sg_conf,
            sync_gateway_version=sync_gateway_upgraded_version,
            url=sg_ip
        )

        time.sleep(10)
        log_info("Checking for sync gateway product info after upgrade")
        verify_sync_gateway_product_info(sg_ip)
        log_info("Checking for sync gateway version after upgrade: {}".format(sync_gateway_upgraded_version))
        verify_sync_gateway_version(sg_ip, sync_gateway_upgraded_version)

    log_info("Upgraded all the sync gateway nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END Sync Gateway cluster upgrade')
    log_info('------------------------------------------')


def create_sgw_sessions_and_configure_replications(sg_client, replicator, authenticator, sg_user_channels, sg, sg_user_name, sg_db, cbl_db, sg_blip_url):
    
    sg_user_password = "password"
    sg_client.create_user(url=sg.admin.admin_url, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels)
    sg_cookie, sg_session = sg_client.create_session(url=sg.admin.admin_url, db=sg_db, name=sg_user_name)

    replicator_authenticator = authenticator.authentication(sg_session, sg_cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    return repl, replicator_authenticator
