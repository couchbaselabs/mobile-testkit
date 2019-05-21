import pdb
import os
import random
import time

from keywords.couchbaseserver import verify_server_version
from libraries.testkit.cluster import Cluster
from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (verify_sg_accel_version,
                                  verify_sync_gateway_version,
                                  verify_sg_accel_product_info,
                                  verify_sync_gateway_product_info,
                                  SyncGateway)
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords import attachment
from couchbase.bucket import Bucket
from keywords.constants import SDK_TIMEOUT
from concurrent.futures import ProcessPoolExecutor, as_completed
from requests.exceptions import HTTPError

from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator


def test_upgrade(params_from_base_test_setup):
    """
    @summary
        The initial versions of SG and CBS has already been provisioned at this point
        We have to upgrade them to the upgraded versions
    """
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    server_version = params_from_base_test_setup['server_version']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    base_url = params_from_base_test_setup["base_url"]
    sg_url = params_from_base_test_setup['target_url']
    sg_admin_url = params_from_base_test_setup['target_admin_url']
    sg_blip_url = params_from_base_test_setup["target_url"]
    num_docs = int(params_from_base_test_setup['num_docs'])
    cbs_platform = params_from_base_test_setup['cbs_platform']
    cbs_toy_build = params_from_base_test_setup['cbs_toy_build']
    cbl_db = params_from_base_test_setup["db"]
    sg_conf = "{}/resources/sync_gateway_configs/sync_gateway_default_functional_tests_{}.json".format(os.getcwd(), mode)

    # Create user and session on SG
    sg_client = MobileRestClient()
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
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name, password=sg_user_password)

    # Starting continuous push replication from TestServer to sync gateway
    log_info("Starting continuous push replication from TestServer to sync gateway")
    replicator_push = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session, cookie, authentication_type="session")

    repl_config_push = replicator_push.configure(target_db=sg_db, source_db=cbl_db, target_url=sg_blip_url, continuous=True, replication_type="push",
                                                 replicator_authenticator=replicator_authenticator, channels=sg_user_channels)

    repl_push = replicator_push.create(repl_config_push)
    replicator_push.start(repl_push)
    replicator_push.wait_until_replicator_idle(repl_push, err_check=False)

    pdb.set_trace()
    # Starting continuous pull replication from sync gateway to TestServer
    log_info("Starting continuous pull replication from sync gateway to TestServer")
    replicator_pull = Replication(base_url)
    repl_config_pull = replicator_pull.configure(target_db=sg_db, source_db=cbl_db, target_url=sg_blip_url, continuous=True, replication_type="pull",
                                                 replicator_authenticator=replicator_authenticator, channels=sg_user_channels)

    repl_pull = replicator_pull.create(repl_config_pull)
    replicator_pull.start(repl_pull)
    replicator_pull.wait_until_replicator_idle(repl_pull, err_check=False)

    pdb.set_trace()
    # Add docs to TestServer
    cbl_db_name = "dbl"
    cbl_db.create_bulk_docs(number=num_docs, id_prefix="cbl_filter", db=cbl_db_name, channels=sg_user_channels)
    doc_ids = cbl_db.getDocIds(cbl_db_name)
    added_docs = cbl_db.getDocuments(cbl_db_name, doc_ids)
    log_info("Added {} docs".format(len(added_docs)))

    pdb.set_trace()
    # start updating docs
    terminator_doc_id = 'terminator'
    with ProcessPoolExecutor() as up:
        # Start updates in background process
        updates_future = up.submit(
            update_docs,
            cbl_db,
            cbl_db_name,
            added_docs,
            terminator_doc_id
        )

        # Supported upgrade process
        # 1. Upgrade SGs first docmeta -> docmeta - CBS 5.0.0 does not support TAP.
        # 2. Upgrade the CBS cluster.
        # 3. Enable import/xattrs on SGs

        # Upgrade SG docmeta -> docmeta
        cluster_util = ClusterKeywords(cluster_config)
        topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
        sync_gateways = topology["sync_gateways"]
        sg_accels = topology["sg_accels"]

        upgrade_sync_gateway(
            sync_gateways,
            sync_gateway_version,
            sync_gateway_upgraded_version,
            sg_conf,
            cluster_config
        )

        if mode == "di":
            upgrade_sg_accel(
                sg_accels,
                sync_gateway_version,
                sync_gateway_upgraded_version,
                sg_conf,
                cluster_config
            )

        # Upgrade CBS
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

        # Restart SGs after the server upgrade
        sg_obj = SyncGateway()
        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting sync gateway {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)
            time.sleep(5)

        if mode == "di":
            ac_obj = SyncGateway()
            for ac in sg_accels:
                ac_ip = host_for_url(ac)
                log_info("Restarting sg accel {}".format(ac_ip))
                ac_obj.restart_sync_gateways(cluster_config=cluster_config, url=ac_ip)
                time.sleep(5)

        if xattrs_enabled:
            # Enable xattrs on all SG/SGAccel nodes
            # cc - Start 1 SG with import enabled, all with XATTRs enabled
            # di - All SGs/SGAccels with xattrs enabled - this will also enable import on SGAccel
            #    - Do not enable import in SG.
            if mode == "cc":
                enable_import = True
            elif mode == "di":
                enable_import = False

            if mode == "di":
                ac_obj = SyncGateway()
                for ac in sg_accels:
                    ac_ip = host_for_url(ac)
                    ac_obj.redeploy_sync_gateway_config(
                        cluster_config=cluster_config,
                        sg_conf=sg_conf,
                        url=ac_ip,
                        sync_gateway_version=sync_gateway_upgraded_version,
                        enable_import=False
                    )

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

        send_changes_termination_doc(
            cbl_db=cbl_db,
            cbl_db_name=cbl_db_name,
            terminator_doc_id=terminator_doc_id,
            terminator_channel=sg_user_channels
        )
        log_info("Waiting for doc updates to complete")
        updated_doc_revs = updates_future.result()

        log_info("Stopping replication from liteserv to sync gateway")
        # Stop repl_one
        replicator_push.stop(repl_config_push)

        log_info("Stopping replication from sync gateway to liteserv")
        # Stop repl_two
        replicator_push.stop(repl_config_pull)

        # Gather the new revs for verification
        log_info("Gathering the updated revs for verification")
        doc_ids = []
        for i in range(len(added_docs)):
            doc_ids.append(added_docs[i]["id"])
            if added_docs[i]["id"] in updated_doc_revs:
                added_docs[i]["rev"] = updated_doc_revs[added_docs[i]["id"]]

        # Verify rev, doc bdy and revision history of all docs
        verify_sg_docs_revision_history(url=sg_admin_url, db=sg_db, added_docs=added_docs)

        if xattrs_enabled:
            # Verify through SDK that there is no _sync property in the doc body
            bucket_name = 'data-bucket'
            sdk_client = Bucket('couchbase://{}/{}'.format(primary_server.host, bucket_name), password='password', timeout=SDK_TIMEOUT)
            log_info("Fetching docs from SDK")
            docs_from_sdk = sdk_client.get_multi(doc_ids)

            log_info("Verifying that there is no _sync property in the docs")
            for i in docs_from_sdk:
                if "_sync" in docs_from_sdk[i].value:
                    raise Exception("_sync section found in docs after upgrade")


def add_client_docs(client, url, db, channels, generator, ndocs, id_prefix, attachments_generator):
    docs = client.add_docs(
        url=url,
        db=db,
        channels=channels,
        generator=generator,
        number=ndocs,
        id_prefix=id_prefix,
        attachments_generator=attachments_generator
    )

    return docs


def add_docs_to_client_task(client, url, db, channels, num_docs):
    docs = []
    docs_per_thread = num_docs // 10
    with ProcessPoolExecutor(max_workers=10) as ad:
        futures = [ad.submit(
            add_client_docs,
            client=client,
            url=url,
            db=db,
            channels=channels,
            generator="simple_user",
            ndocs=docs_per_thread,
            id_prefix="ls_db_upgrade_doc_{}".format(i),
            attachments_generator=attachment.generate_png_1_1
        ) for i in range(10)]

        for future in as_completed(futures):
            docs.extend(future.result())

    return docs


def verify_sg_docs_revision_history(url, db, added_docs):
    sg_client = MobileRestClient()
    expected_doc_map = {added_doc["id"]: added_doc["rev"] for added_doc in added_docs}
    doc_ids = expected_doc_map.keys()

    log_info("Bulk getting docs from sync gateway")
    docs = sg_client.get_bulk_docs(url, db, doc_ids, rev_history="true")
    assert len(docs[0]) == len(doc_ids)

    for doc in docs:
        for doc_dict in doc:
            rev = doc_dict["_rev"]
            rev_gen = int(rev.split("-")[0])
            doc_id = doc_dict["_id"]
            # Verify meta data
            log_info("Verifying that doc {} has rev {}".format(doc_id, expected_doc_map[doc_id]))
            assert rev == expected_doc_map[doc_id]
            log_info("Doc {}: Expected number of revs: {}, Actual revs: {}".format(doc_id, rev_gen, len(doc_dict["_revisions"]["ids"])))
            assert len(doc_dict["_revisions"]["ids"]) == rev_gen
            log_info("Verifying that doc {} is associated with sg_user_channel channel".format(doc_id))
            assert doc_dict["channels"][0] == "sg_user_channel"
            # Verify doc body
            log_info("Verifying doc body for {}".format(doc_id))
            assert "guid" in doc_dict
            assert "index" in doc_dict
            assert "latitude" in doc_dict
            assert "email" in doc_dict
            assert "picture" in doc_dict
            assert len(doc_dict["tags"]) == 3
            assert "date_time_added" in doc_dict
            assert "company" in doc_dict
            assert "eyeColor" in doc_dict
            assert "phone" in doc_dict
            assert "updates" in doc_dict
            assert "address" in doc_dict
            assert len(doc_dict["friends"]) == 2
            assert "isActive" in doc_dict
            assert "about" in doc_dict
            assert "name" in doc_dict
            assert "age" in doc_dict
            assert "registered" in doc_dict
            assert "longitude" in doc_dict
            assert "_attachments" in doc_dict
            assert "range" in doc_dict
            assert "balance" in doc_dict
            log_info("Verified doc body for {}".format(doc_id))


def send_changes_termination_doc(cbl_db, cbl_db_name, terminator_doc_id, terminator_channel):
    doc_body = {}
    doc_body["channels"] = terminator_channel
    doc_body["_id"] = terminator_doc_id
    doc_body["foo"] = "bar"
    cbl_db.saveDocument(database=cbl_db_name, document=doc_body)


def update_docs(cbl_db, added_docs, cbl_db_name, terminator_doc_id):
    log_info("Starting doc updates")
    current_user_doc_ids = []
    for doc in added_docs:
        current_user_doc_ids.append(doc["id"])

    docs_per_update = 3
    doc_revs = {}

    while True:
        try:
            cbl_db.getDocument(database=cbl_db_name, doc_id=terminator_doc_id)
            log_info("update_docs: Found termination doc")
            log_info("update_docs: Updated {} docs".format(len(doc_revs.keys())))
            return doc_revs
        except HTTPError:
            log_info("Termination doc not found")

        user_docs_subset_to_update = []
        for _ in range(docs_per_update):
            random_doc_id = random.choice(current_user_doc_ids)
            user_docs_subset_to_update.append(random_doc_id)

        for doc_id in user_docs_subset_to_update:
            log_info("Updating doc_id: {}".format(doc_id))
            doc = cbl_db.getDocument(database=cbl_db_name, doc_id=doc_id)
            doc['updates'] += 1
            doc['rev'] = doc['_rev']
            cbl_db.updateDocument(database=cbl_db_name, doc_id=doc_id, data=doc)
            new_doc = cbl_db.getDocument(database=cbl_db_name, doc_id=doc_id)
            doc_revs[doc_id] = new_doc['_rev']
            time.sleep(2)

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
        log_info("Checking for the server version: {}".format(server_upgraded_version))
        verify_server_version(server.host, server_upgraded_version)
        time.sleep(10)

    # Upgrade the primary server
    primary_server_services = "kv,index,n1ql"
    log_info("Checking for the server version: {}".format(server_version))
    verify_server_version(primary_server.host, server_version)
    log_info("Rebalance out server: {}".format(primary_server.host))
    secondary_server.rebalance_out(server_urls, primary_server)
    log_info("Upgrading the server: {}".format(primary_server.host))
    secondary_server.upgrade_server(cluster_config=cluster_config, server_version_build=server_upgraded_version, target=primary_server.host, cbs_platform=cbs_platform, toy_build=toy_build)
    log_info("Adding the node back to the cluster: {}".format(primary_server.host))
    secondary_server.add_node(primary_server, services=primary_server_services)
    log_info("Rebalance in server: {}".format(primary_server.host))
    secondary_server.rebalance_in(server_urls, primary_server)
    log_info("Checking for the server version: {}".format(server_upgraded_version))
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


def upgrade_sg_accel(sg_accels, sync_gateway_version, sync_gateway_upgraded_version, sg_conf, cluster_config):
    log_info('------------------------------------------')
    log_info('START SG Accel cluster upgrade')
    log_info('------------------------------------------')

    ac_obj = SyncGateway()

    for ac in sg_accels:
        ac_ip = host_for_url(ac)
        log_info("Checking for sg_accel version before upgrade: {}".format(sync_gateway_version))
        verify_sg_accel_version(ac_ip, sync_gateway_version)
        log_info("Upgrading sg_accel: {}".format(ac_ip))
        ac_obj.upgrade_sync_gateways(
            cluster_config=cluster_config,
            sg_conf=sg_conf,
            sync_gateway_version=sync_gateway_upgraded_version,
            url=ac_ip
        )
        time.sleep(10)

        log_info("Checking for sg accel product info after upgrade")
        verify_sg_accel_product_info(ac_ip)
        log_info("Checking for sg accel version after upgrade: {}".format(sync_gateway_upgraded_version))
        verify_sg_accel_version(ac_ip, sync_gateway_upgraded_version)

    log_info("Upgraded all the sg accel nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END SG Accel cluster upgrade')
    log_info('------------------------------------------')
