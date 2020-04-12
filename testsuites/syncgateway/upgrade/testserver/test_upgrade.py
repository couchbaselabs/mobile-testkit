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
from utilities.cluster_config_utils import persist_cluster_config_environment_prop

from libraries.testkit.cluster import Cluster
from keywords import attachment
from CBLClient.Authenticator import Authenticator
from CBLClient.Document import Document
from CBLClient.Replication import Replication


def test_upgrade(params_from_base_test_setup):
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
    sg_blip_url = params_from_base_test_setup["target_url"]
    num_docs = int(params_from_base_test_setup['num_docs'])
    cbs_platform = params_from_base_test_setup['cbs_platform']
    cbs_toy_build = params_from_base_test_setup['cbs_toy_build']
    cbl_db = params_from_base_test_setup["source_db"]
    cbl_db2 = params_from_base_test_setup["source_db2"]
    db = params_from_base_test_setup["db"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_ip = params_from_base_test_setup["sg_ip"]
    sg_conf = "{}/resources/sync_gateway_configs/sync_gateway_default_functional_tests_{}.json".format(os.getcwd(), mode)

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
        need_to_redeploy = True
        if upgraded_delta_sync_enabled:
            log_info("Running with delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', True)
        else:
            log_info("Running without delta sync after upgrade")
            persist_cluster_config_environment_prop(cluster_config, 'delta_sync_enabled', False)

    # 1. Create user, session and docs on SG
    sg_client = MobileRestClient()
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config)

    sg_user_channels = ["sg_user_channel"]
    sg_db = "db"
    sg_user_name = "sg_user"
    sg_user_password = "password"
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=sg_user_name,
        password=sg_user_password,
        channels=sg_user_channels
    )

    doc_obj = Document(base_url)
    db.create_bulk_docs(number=num_docs, id_prefix="cbl_filter", db=cbl_db, channels=sg_user_channels, attachments_generator=attachment.generate_2_png_10_10)
    doc_ids = db.getDocIds(cbl_db, limit=num_docs)
    added_docs = db.getDocuments(cbl_db, doc_ids)
    log_info("Added {} docs".format(len(added_docs)))

    # 2. Starting continuous push_pull replication from TestServer to sync gateway
    log_info("Starting continuous push pull replication from TestServer to sync gateway")
    replicator = Replication(base_url)
    sg_cookie, sg_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(sg_session, sg_cookie, authentication_type="session")
    repl_config = replicator.configure(cbl_db, sg_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    # Start 2nd replicator to verify docs with attachments gets replicated after the upgrade for one shot replications
    sg_cookie, sg_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)
    sg_cookie1, sg_session1 = sg_client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name)
    repl_config1 = replicator.configure(cbl_db2, sg_blip_url, continuous=False, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator)
    repl1 = replicator.create(repl_config1)
    replicator.start(repl1)
    replicator.wait_until_replicator_idle(repl1)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=2, id_prefix="sgw_docs1", channels=sg_user_channels, generator="simple_user", attachments_generator=attachment.generate_2_png_10_10)
    # 3. Start a thread to keep updating docs on CBL
    terminator_doc_id = 'terminator'
    with ProcessPoolExecutor() as up:
        # Start updates in background process
        updates_future = up.submit(
            update_docs,
            db,
            cbl_db,
            added_docs,
            doc_obj,
            terminator_doc_id
        )

        # 4. Upgrade SGW one by one on cluster config list
        cluster_util = ClusterKeywords(cluster_config)
        topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
        sync_gateways = topology["sync_gateways"]

        upgrade_sync_gateway(
            sync_gateways,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sg_conf,
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

        upgrade_server_cluster(
            servers,
            primary_server,
            secondary_server,
            server_version,
            server_upgraded_version,
            server_urls,
            cluster_config,
            cbs_platform,
            toy_build=cbs_toy_build
        )

        # 6. Restart SGWs after the server upgrade
        sg_obj = SyncGateway()
        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)
            time.sleep(5)

        if need_to_redeploy:
            # Enable xattrs on all SG/SGAccel nodes
            # cc - Start 1 SG with import enabled, all with XATTRs enabled
            #    - Do not enable import in SG.
            if mode == "cc":
                enable_import = True

            sg_obj = SyncGateway()
            for sg in sync_gateways:
                sg_ip = host_for_url(sg["admin"])
                sg_obj.redeploy_sync_gateway_config(
                    cluster_config=cluster_config,
                    sg_conf=sg_conf,
                    url=sg_ip,
                    sync_gateway_version=sync_gateway_upgraded_version,
                    enable_import=enable_import
                )
                enable_import = False
                # Check Import showing up on all nodes
        
        db.create_bulk_docs(number=1, id_prefix=terminator_doc_id, db=cbl_db, channels=sg_user_channels)
        log_info("Waiting for doc updates to complete")
        updated_doc_revs = updates_future.result()

        # set up another replicator to verify attachments replicated after the upgrade
        repl_config2 = replicator.configure(cbl_db2, sg_blip_url, continuous=True, channels=sg_user_channels, replication_type="push_pull", replicator_authenticator=replicator_authenticator)
        repl2 = replicator.create(repl_config2)
        replicator.start(repl2) 
        log_info("waiting for the replication to complete")
        replicator.wait_until_replicator_idle(repl2, max_times=3000)
        log_info("Stopping replication between testserver and sync gateway")
        replicator.stop(repl2)
        replicator.stop(repl)

        # 7. Gather CBL docs new revs for verification
        log_info("Gathering the updated revs for verification")
        doc_ids = []
        for doc_id in added_docs:
            doc_ids.append(doc_id)
            if doc_id in updated_doc_revs:
                added_docs[doc_id]["numOfUpdates"] = updated_doc_revs[doc_id]

        # 8. Compare rev id, doc body and revision history of all docs on both CBL and SGW
        verify_sg_docs_revision_history(sg_admin_url, db, cbl_db2, num_docs, sg_db=sg_db, added_docs=added_docs, terminator=terminator_doc_id)

        # 9. If xattrs enabled, validate CBS contains _sync records for each doc
        if upgraded_xattrs_enabled:
            # Verify through SDK that there is no _sync property in the doc body
            bucket_name = 'data-bucket'
            sdk_client = Bucket('couchbase://{}/{}'.format(primary_server.host, bucket_name), password='password', timeout=SDK_TIMEOUT)
            log_info("Fetching docs from SDK")
            docs_from_sdk = sdk_client.get_multi(doc_ids)

            log_info("Verifying that there is no _sync property in the docs")
            for i in docs_from_sdk:
                if "_sync" in docs_from_sdk[i].value:
                    raise Exception("_sync section found in docs after upgrade")


def verify_sg_docs_revision_history(url, db, cbl_db2, num_docs, sg_db, added_docs, terminator):
    sg_client = MobileRestClient()
    sg_docs = sg_client.get_all_docs(url=url, db=sg_db, include_docs=True)["rows"]
    cbl_doc_ids2 = db.getDocIds(cbl_db2, limit=num_docs)
    cbl_docs2 = db.getDocuments(cbl_db2, cbl_doc_ids2)
    num_sg_docs_in_cbldb2 = 0
    expected_doc_map = {}
    for doc in added_docs:
        if "numOfUpdates" in added_docs[doc]:
            expected_doc_map[doc] = added_docs[doc]["numOfUpdates"] - 1
        else:
            expected_doc_map[doc] = 1
    print("all cbl_docs 2 are ... ", cbl_docs2)
    for doc in cbl_docs2:
        if "sgw_docs" in doc:
            num_sg_docs_in_cbldb2 += 1
            assert '_attachments' in cbl_docs2[doc], "_attachments does not exist in doc created in sgw"
    assert num_sg_docs_in_cbldb2 == 2, "sgw docs are not replicated to cbl db2"
    for doc in sg_docs:
        if "sgw_docs" not in doc['id']:
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


def update_docs(db, cbl_db, added_docs, doc_obj, terminator_doc_id_prefix):
    log_info("Starting doc updates")
    current_user_doc_ids = []
    for doc in added_docs:
        current_user_doc_ids.append(doc)

    docs_per_update = 3
    doc_revs = {}
    terminator_doc_id = "{}_0".format(terminator_doc_id_prefix)
    terminator_not_found_msg = "Termination doc not found"

    while True:
        log_info("randomly update docs waiting for terminator arrive...")
        try:
            term_doc = db.getDocument(cbl_db, terminator_doc_id)
            if term_doc == -1:
                log_info(terminator_not_found_msg)
            else:
                doc_type = term_doc.__class__.__name__
                if doc_type == "MemoryPointer":
                    log_info("update_docs: Found termination doc")
                    log_info("update_docs: Updated {} docs".format(len(doc_revs)))
                    return doc_revs
                else:
                    log_info("update_docs: doc object is retrieved correctly")
        except Exception:
            log_info(terminator_not_found_msg)

        user_docs_subset_to_update = []
        for _ in range(docs_per_update):
            random_doc_id = random.choice(current_user_doc_ids)
            user_docs_subset_to_update.append(random_doc_id)

        cbl_db_docs_to_update = {}
        for doc_id in user_docs_subset_to_update:
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
            cbl_db_docs_to_update[doc_id] = doc_body
            db.updateDocument(database=cbl_db, doc_id=doc_id, data=doc_body)

        for doc_id, doc_body in list(cbl_db_docs_to_update.items()):
            new_doc = db.getDocument(cbl_db, doc_id)
            doc_revs[doc_id] = doc_obj.toMap(new_doc)['numOfUpdates']

        time.sleep(5)


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
