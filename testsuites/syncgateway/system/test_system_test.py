import time

from couchbase.bucket import Bucket
from requests import Session
from requests.exceptions import HTTPError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import couchbaseserver
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import SyncGateway
from keywords.utils import log_info


def test_system_test(params_from_base_test_setup):
    server_seed_docs = int(params_from_base_test_setup["server_seed_docs"])
    # max_docs = int(params_from_base_test_setup["max_docs"])
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    cluster_helper = ClusterKeywords()
    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    cbs_admin_url = cbs_url.replace("8091", "8092")
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    bucket_name = cb_server.get_bucket_names()[0]
    cbs_ip = cb_server.host

    # Stop SG before loading the server
    sg_url = topology["sync_gateways"][0]["public"]
    # sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_util = SyncGateway()
    sg_util.stop_sync_gateway(cluster_config=cluster_config, url=sg_url)

    # Set the default value to 404 - view not created yet
    sg_views = {
        'sync_gateway_access': ["access"],
        'sync_gateway_access_vbseq': ["access_vbseq"],
        'sync_gateway_channels': ["channels"],
        'sync_gateway_role_access': ["role_access"],
        'sync_gateway_role_access_vbseq': ["role_access_vbseq"],
        'sync_housekeeping': [
            "all_bits",
            "all_docs",
            "import",
            "old_revs",
            "principals",
            "sessions",
            "tombstones"
        ]
    }

    sg_conf_name = "sync_gateway_default"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Delete the SG views before seeding the server
    # We want to see how long does it take for SG views to get created
    headers = {"Content-Type": "application/json"}
    cbs_session = Session()
    cbs_session.headers = headers
    cbs_session.auth = ('Administrator', 'password')

    for view in sg_views:
        log_info("Deleting view: {}".format(view))
        try:
            resp = cbs_session.delete("{}/{}/_design/{}".format(cbs_admin_url, bucket_name, view))
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 404:
                log_info("View already deleted: {}".format(view))
            else:
                raise

    # Seed the server with server_seed_docs number of docs
    log_info("Seeding {} with {} docs".format(cbs_ip, server_seed_docs))
    bucket = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=300)
    docs = {'doc_{}'.format(i): {'foo': 'bar'} for i in range(server_seed_docs)}
    bucket.upsert_multi(docs)

    # Start SG
    sg_util.start_sync_gateway(cluster_config=cluster_config, url=sg_url, config=sg_conf)
    # It takes a couple of seconds for the view indexing to begin
    time.sleep(5)

    # Wait for the views to be ready
    start = time.time()
    for view in sg_views:
        for index in sg_views[view]:
            log_info("Waiting for view {}/{} to be finished".format(view, index))
            resp = cbs_session.get("{}/{}/_design/{}/_view/{}?stale=false".format(cbs_admin_url, bucket_name, view, index))
            resp.raise_for_status()

    end = time.time()
    log_info("Views creation took {} seconds".format(end - start))

    # Load 100,000 docs via SG REST API
    #   - Write 1,000 1K docs with attachments to Server and continually update to 1,000,000 1K docs
    #   with attachments using 180 users concurrently
    # Start timer
    # Doc ramp up time to go to a million doc
    # Doc batch size - bulk add x number of docs at a time
    # Doc sleep time - sleep between bulk adds
