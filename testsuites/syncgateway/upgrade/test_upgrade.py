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
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import HTTPError


def test_upgrade(params_from_base_test_setup):
    """ The initial versions of SG and CBS has already been provisioned at this point
        We have to upgrade them to the upgraded versions
    """
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']
    ls_url = params_from_base_test_setup["ls_url"]
    server_version = params_from_base_test_setup['server_version']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    server_upgraded_version = params_from_base_test_setup['server_upgraded_version']
    sync_gateway_upgraded_version = params_from_base_test_setup['sync_gateway_upgraded_version']
    sg_url = params_from_base_test_setup['sg_url']
    sg_admin_url = params_from_base_test_setup['sg_admin_url']
    num_docs = int(params_from_base_test_setup['num_docs'])
    sg_conf = "{}/resources/sync_gateway_configs/sync_gateway_default_functional_tests_{}.json".format(os.getcwd(), mode)

    # Add data to liteserv
    client = MobileRestClient()
    log_info("ls_url: {}".format(ls_url))
    ls_db = client.create_database(ls_url, name="ls_db")

    # Create user and session on SG
    sg_user_channels = ["sg_user_channel"]
    sg_db = "db"
    sg_user_name = "sg_user"
    sg_user_password = "password"
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=sg_user_name,
        password=sg_user_password,
        channels=sg_user_channels
    )
    sg_session = client.create_session(url=sg_admin_url, db=sg_db, name=sg_user_name, password=sg_user_password)

    # Start continuous push pull replication ls_db_one <-> sg_db_one
    log_info("Starting replication from liteserv to sync gateway")
    repl_one = client.start_replication(
        url=ls_url, continuous=True,
        from_db=ls_db,
        to_url=sg_url, to_db=sg_db, to_auth=sg_session
    )
    client.wait_for_replication_status_idle(ls_url, repl_one)

    log_info("Starting replication from sync gateway to liteserv")
    client.start_replication(
        url=ls_url, continuous=True,
        from_url=sg_url, from_db=sg_db, from_auth=sg_session,
        to_db=ls_db
    )

    # Add docs to liteserv
    # added_docs = client.add_docs(url=ls_url, db=ls_db, channels=sg_user_channels, generator="simple_user", number=num_docs, id_prefix="ls_db_upgrade_doc", attachments_generator=attachment.generate_png_1_1)
    added_docs = add_docs_to_client_task(
        client=client,
        url=ls_url,
        db=ls_db,
        channels=sg_user_channels,
        num_docs=num_docs
    )
    log_info("Added {} docs".format(len(added_docs)))

    # start updating docs
    terminator_doc_id = 'terminator'
    with ThreadPoolExecutor() as up:
        # Start updates in background process
        updates_future = up.submit(
            update_docs,
            client,
            ls_url,
            ls_db,
            added_docs,
            sg_session,
            terminator_doc_id
        )

        # Supported upgrade process
        # 1. Upgrade SGs first docmeta -> docmeta - CBS 5.0.0 does not support TAP.
        # 2. Upgrade the CBS cluster.
        # 3. Enable import/xattrs on SGs

        # Upgrade SG docmeta -> docmeta
        cluster_util = ClusterKeywords()
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
            cluster_config
        )

        # Restart SGs after the server upgrade
        sg_obj = SyncGateway()
        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Restarting {}".format(sg_ip))
            sg_obj.restart_sync_gateways(cluster_config=cluster_config, url=sg_ip)

        if mode == "di":
            ac_obj = SyncGateway()
            for ac in sg_accels:
                ac_ip = host_for_url(ac["admin"])
                log_info("Restarting {}".format(ac_ip))
                ac_obj.restart_sync_gateways(cluster_config=cluster_config, url=ac_ip)
        # Check RBAC user
        if xattrs_enabled:
            # Enable xattrs on all SG/SGAccel nodes
            # cc - Start 1 SG with import enabled, all with XATTRs enabled
            # di - All SGs/SGAccels with xattrs enabled - this will also enable import on SGAccel
            #    - Do not enable import in SG.
            # Enable xattrs on all nodes
            if mode == "cc":
                enable_import = True
            elif mode == "di":
                enable_import = False

            sg_obj = SyncGateway()
            for sg in sync_gateways:
                sg_ip = host_for_url(sg["admin"])
                sg_obj.enable_import_xattrs(
                    cluster_config=cluster_config,
                    sg_conf=sg_conf,
                    url=sg_ip,
                    enable_import=enable_import
                )
                enable_import = False
                # Check Import showing up on all nodes

            if mode == "di":
                ac_obj = SyncGateway()
                for ac in sg_accels:
                    ac_ip = host_for_url(sg["admin"])
                    ac_obj.enable_import_xattrs(
                        cluster_config=cluster_config,
                        sg_conf=sg_conf,
                        url=ac_ip,
                        enable_import=False
                    )

        send_changes_termination_doc(sg_url, sg_db, sg_session, terminator_doc_id, sg_user_channels)
        updated_doc_revs = updates_future.result()

        log_info("Stopping replication from liteserv to sync gateway")
        # Stop repl_one
        client.stop_replication(
            url=ls_url, continuous=True,
            from_db=ls_db,
            to_url=sg_url, to_db=sg_db, to_auth=sg_session
        )

        log_info("Stopping replication from sync gateway to liteserv")
        # Stop repl_two
        client.stop_replication(
            url=ls_url, continuous=True,
            from_url=sg_url, from_db=sg_db, from_auth=sg_session,
            to_db=ls_db
        )
        # Gather the new revs for verification
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
            docs_from_sdk = sdk_client.get_multi(doc_ids)

            for i in docs_from_sdk:
                if "_sync" in docs_from_sdk[i].value:
                    raise Exception("sync section found in docs after upgrade")


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
    with ThreadPoolExecutor() as ad:
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


def send_changes_termination_doc(sg_url, sg_db, auth, terminator_doc_id, terminator_channel):
    sg_client = MobileRestClient()
    log_info('Sending changes termination doc for all users')
    doc = {'_id': terminator_doc_id, 'channels': terminator_channel}
    sg_client.add_doc(url=sg_url, db=sg_db, doc=doc, auth=auth)


def update_docs(client, ls_url, ls_db, added_docs, auth, terminator_doc_id):
    log_info("Starting doc updates")
    current_user_doc_ids = []
    for doc in added_docs:
        current_user_doc_ids.append(doc["id"])

    docs_per_update = 3
    doc_revs = {}

    while True:
        try:
            client.get_doc(url=ls_url, db=ls_db, doc_id=terminator_doc_id, auth=auth)
            log_info("Found termination doc")
            return doc_revs
        except HTTPError:
            log_info("Termination doc not found")

        user_docs_subset_to_update = []
        for _ in range(docs_per_update):
            random_doc_id = random.choice(current_user_doc_ids)
            user_docs_subset_to_update.append(random_doc_id)

        for doc_id in user_docs_subset_to_update:
            log_info("Updating doc_id: {}".format(doc_id))
            doc = client.get_doc(url=ls_url, db=ls_db, doc_id=doc_id, auth=auth)
            doc['updates'] += 1
            client.put_doc(url=ls_url, db=ls_db, doc_id=doc_id, doc_body=doc, rev=doc['_rev'], auth=auth)
            new_doc = client.get_doc(url=ls_url, db=ls_db, doc_id=doc_id, auth=auth)
            doc_revs[doc_id] = new_doc['_rev']
            time.sleep(2)

        time.sleep(5)


def upgrade_server_cluster(servers, primary_server, secondary_server, server_version, server_upgraded_version, server_urls, cluster_config):
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
        primary_server.upgrade_server(cluster_config, server_upgraded_version, target=server.host)
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
    secondary_server.upgrade_server(cluster_config, server_upgraded_version, target=primary_server.host)
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

    log_info("Upgraded all the sync gateway nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END Sync Gateway cluster upgrade')
    log_info('------------------------------------------')


def upgrade_sg_accel(sg_accels, sync_gateway_version, sync_gateway_upgraded_version, sg_conf, cluster_config):
    log_info('------------------------------------------')
    log_info('START SG Accel cluster upgrade')
    log_info('------------------------------------------')

    for ac in sg_accels:
        ac_ip = host_for_url(ac["admin"])
        ac_obj = SyncGateway()
        verify_sg_accel_product_info(ac_ip)
        log_info("Checking for sg_accel version: {}".format(sync_gateway_version))
        verify_sg_accel_version(ac_ip, sync_gateway_version)
        log_info("Upgrading sg_accel: {}".format(ac_ip))
        ac_obj.upgrade_sync_gateways(
            cluster_config=cluster_config,
            sg_conf=sg_conf,
            sync_gateway_version=sync_gateway_upgraded_version,
            url=ac_ip
        )
        time.sleep(10)

        verify_sg_accel_product_info(ac_ip)
        log_info("Checking for sunc gateway version: {}".format(sync_gateway_upgraded_version))
        verify_sg_accel_version(ac_ip, sync_gateway_upgraded_version)

    log_info("Upgraded all the sg accel nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END SG Accel cluster upgrade')
    log_info('------------------------------------------')
