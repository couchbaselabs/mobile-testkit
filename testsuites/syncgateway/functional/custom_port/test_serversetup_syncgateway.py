import pytest
import json
import os
import time

from keywords.remoteexecutor import RemoteExecutor
from keywords.SyncGateway import SyncGateway, sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from keywords.utils import host_for_url
from keywords import couchbaseserver
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from libraries.provision.install_sync_gateway import get_buckets_from_sync_gateway_config
from utilities.cluster_config_utils import get_cbs_servers


@pytest.fixture(scope="function")
def teardown_clear_custom_port(params_from_base_test_setup):
    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup['mode']
    sg_conf_name = 'sync_gateway_default_functional_tests'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster = Cluster(config=cluster_conf)

    yield {
        "cluster_conf": cluster_conf,
        "cluster": cluster,
        "sg_conf": sg_conf,
        "mode": mode

    }
    for server in cluster.servers:
        remote_executor = RemoteExecutor(host_for_url(server.url))
        cb_server = couchbaseserver.CouchbaseServer(server.url)
        cb_server.stop()
        command = "cp /opt/couchbase/etc/couchbase/static_config.bak /opt/couchbase/etc/couchbase/static_config \
                   && cp /opt/couchbase/var/lib/couchbase/config/config.dat.bak /opt/couchbase/var/lib/couchbase/config/config.dat"
        remote_executor.execute(command)
        cb_server.start()
    cluster.reset(sg_config_path=sg_conf)


@pytest.mark.syncgateway
@pytest.mark.server
def test_syncgateway_with_customPort_couchbaseServer(params_from_base_test_setup, teardown_clear_custom_port):
    """
        @summary:
        1.Add custom port on server
            stop couchbase server
            Add entries to the file /opt/couchbase/etc/couchbase/static_config at the end
                {rest_port, 9000}
                {memcached_port, 9050}.
                {ssl_rest_port, 1900}.
                {memcached_ssl_port, 9057}.
            save the file
            rm the file /opt/couchbase/var/lib/couchbase/config/config.dat
            start the couchbase server
        3. Create cluster and bucket again as config.dat is removed
        2. Restart sync gateway with new custom port
        3. Verify sync gateway starts successfully
    """
    mode = teardown_clear_custom_port['mode']
    sg_conf_name = 'sync_gateway_default_functional_tests'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_conf = teardown_clear_custom_port["cluster_conf"]
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

    cluster = teardown_clear_custom_port["cluster"]
    cluster.reset(sg_config_path=sg_conf)
    ansible_runner = AnsibleRunner(cluster_conf)

    custom_port = "9000"
    memcached_ssl_port = "9057"

    for server in cluster.servers:
        cb_server = couchbaseserver.CouchbaseServer(server.url)
        cb_server.stop()
        cbs_target = host_for_url(server.url)
        remote_executor = RemoteExecutor(cbs_target)
        command = "cp /opt/couchbase/etc/couchbase/static_config /opt/couchbase/etc/couchbase/static_config.bak" \
            "&& cp /opt/couchbase/var/lib/couchbase/config/config.dat /opt/couchbase/var/lib/couchbase/config/config.dat.bak"
        remote_executor.execute(command)
        command = "echo {rest_port, 9000}. >> /opt/couchbase/etc/couchbase/static_config " \
            "&& echo {memcached_port, 9050}. >> /opt/couchbase/etc/couchbase/static_config " \
            "&& echo {ssl_rest_port, 1900}. >> /opt/couchbase/etc/couchbase/static_config " \
            "&& echo {memcached_ssl_port, 9057}. >> /opt/couchbase/etc/couchbase/static_config " \
            "&& rm -rf /opt/couchbase/var/lib/couchbase/config/config.dat"
        remote_executor.execute(command)
        cb_server.url = "http://{}:{}".format(host_for_url(server.url), custom_port)
        cb_server.start(custom_port=True)

    couchbase_server_url = cluster_topology["couchbase_servers"][0]
    couchbase_server_url = couchbase_server_url.replace("8091", custom_port)
    with open("{}.json".format(cluster_conf)) as f:
            cluster = json.loads(f.read())
    server_version = cluster["environment"]["server_version"]
    # configuring cluster
    status = ansible_runner.run_ansible_playbook(
        "configure-couchbase-server.yml",
        extra_vars={
            "couchbase_server_package_base_url": couchbase_server_url,
            "couchbase_server_package_name": server_version,
            "ipv6_enabled": cluster["environment"]["ipv6_enabled"],
            "couchbase_server_admin_port": custom_port
        }
    )
    if status != 0:
        raise ProvisioningError("Failed to configure Couchbase Server")

    # Creating bucket with cli
    sg_conf_path = os.path.abspath(sg_conf)
    bucket_names = get_buckets_from_sync_gateway_config(sg_conf_path)
    server_url = cluster_topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(server_url)
    remote_executor = RemoteExecutor(host_for_url(server_url))
    command = "/opt/couchbase/bin/couchbase-cli bucket-create -c localhost:{} -u Administrator -p password --bucket {} --bucket-type couchbase  --enable-flush 1 --bucket-ramsize 1024".format(custom_port, bucket_names[0])
    remote_executor.execute(command)
    command = "/opt/couchbase/bin/couchbase-cli user-manage -c localhost:{} -u Administrator -p password --rbac-username {} --roles admin --auth-domain local --set".format(custom_port, bucket_names[0])
    remote_executor.execute(command)
    sg_helper = SyncGateway()
    sgws = cluster["sync_gateways"]
    cbs_ips = get_cbs_servers(cluster_conf)
    for sg in sgws:
        sgw_remote_executor = RemoteExecutor(sg["ip"])
        if ssl_enabled:
            command = "sed -i 's/:11207//g' /home/sync_gateway/sync_gateway.json".format(memcached_ssl_port)
        else:
            command = "sed -i 's/:8091//g' /home/sync_gateway/sync_gateway.json".format(custom_port)
        for cbs_ip in cbs_ips:
            if ssl_enabled:
                command = "sed -i 's/{}/{}:{}/g' /home/sync_gateway/sync_gateway.json".format(cbs_ip, cbs_ip, memcached_ssl_port)
            else:
                command = "sed -i 's/{}/{}:{}/g' /home/sync_gateway/sync_gateway.json".format(cbs_ip, cbs_ip, custom_port)
        sgw_remote_executor.execute(command)

    sg_helper.restart_sync_gateways(cluster_conf)


@pytest.mark.syncgateway
@pytest.mark.server
def test_sgw_server_alternative_address(params_from_base_test_setup, setup_alternative_address):
    """
        @summary:
        1.Assign an alternate address on the server and ports
        2. Restart sync gateway after alternate address has changed
        3. Verify sync gateway starts successfully
    """

    mode = params_from_base_test_setup['mode']
    sg_conf_name = 'sync_gateway_default_functional_tests'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cluster = setup_alternative_address["cluster"]
    cluster_conf = setup_alternative_address["cluster_config"]

    sg_client = MobileRestClient()
    sg_db = 'db'

    cluster.reset(sg_config_path=sg_conf)
    sg_helper = SyncGateway()
    with open("{}.json".format(cluster_conf)) as f:
        cluster_json = json.loads(f.read())
    sgws = cluster_json["sync_gateways"]
    couchbase_server_url = cluster_topology["couchbase_servers"][0]
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    cb_server = couchbaseserver.CouchbaseServer(couchbase_server_url)
    bucket_name = cb_server.get_bucket_names()[0]
    for sg in sgws:
        sgw_remote_executor = RemoteExecutor(sg["ip"])
        command = "sed -i 's/http/couchbase/g' /home/sync_gateway/sync_gateway.json"
        sgw_remote_executor.execute(command)
        command = "sed -i 's/:8091//g' /home/sync_gateway/sync_gateway.json"
        sgw_remote_executor.execute(command)
    # use the config with alternate ip address and verify that
    sg_helper.restart_sync_gateways(cluster_conf)

    # Create a document in server via SDK
    docs_to_add = {}
    sdk_client = cb_server.get_bucket_connection(couchbase_server_url, bucket_name, ssl_enabled, cluster)
    docs = document.create_docs('sdk', number=1, channels=['created_via_sdk'])
    for doc in docs:
        docs_to_add[doc['sgw_uni_id']] = doc
    sdk_client.upsert_multi(docs_to_add)
    # Verify import_count stats get incremented
    if sync_gateway_version >= "2.5.0":
        for i in range(10):
            expvars = sg_client.get_expvars(sg_admin_url)
            if expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"] == 1:
                break
            else:
                time.sleep(1)
    assert expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"] == 1, "import_count is not incremented"


@pytest.fixture(scope="function")
def setup_alternative_address(params_from_base_test_setup):
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster = Cluster(config=cluster_config)
    cb_ip_series = "10.63.34.4"

    i = 0
    for server in cluster.servers:
        i = i + 1
        command = "curl -v -X PUT -u Administrator:password "\
            "{}/node/controller/setupAlternateAddresses/external "\
            "-d hostname={}{} -d mgmt=8091 -d kv=11210 -d mgmtSSL=18091 -d kvSSL=11207 -d n1ql=8093 -d n1qlSSL=18093 -d capi=8092 -d capiSSL=18092".format(server.url, cb_ip_series, i)
        os.system(command)
    yield{
        "cluster_config": cluster_config,
        "cluster": cluster
    }

    for server in cluster.servers:
        i = i + 1
        command = "curl -v -X DELETE -u Administrator:password "\
            "{}/node/controller/setupAlternateAddresses/external ".format(server.url, cb_ip_series, i)
        os.system(command)
