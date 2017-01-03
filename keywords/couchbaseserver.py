import time
import json
import requests
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests import Session

from couchbase.bucket import Bucket
from couchbase.exceptions import ProtocolError
from couchbase.exceptions import TemporaryFailError
from couchbase.exceptions import NotFoundError


import keywords.constants
from keywords.RemoteExecutor import RemoteExecutor
from keywords.exceptions import CBServerError
from keywords.exceptions import ProvisioningError
from keywords.exceptions import TimeoutError
from keywords.utils import log_r
from keywords.utils import log_info
from keywords.utils import log_debug
from keywords.utils import log_error


def get_server_version(host):
    resp = requests.get("http://Administrator:password@{}:8091/pools".format(host))
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    # Actual version is the following format 4.1.1-5914-enterprise
    running_server_version = resp_obj["implementationVersion"]
    running_server_version_parts = running_server_version.split("-")

    # Return version in the formatt 4.1.1-5487
    return "{}-{}".format(running_server_version_parts[0], running_server_version_parts[1])


def verify_server_version(host, expected_server_version):
    running_server_version = get_server_version(host)
    expected_server_version_parts = expected_server_version.split("-")

    # Check both version parts if expected version contains a build
    if len(expected_server_version_parts) == 2:
        # 4.1.1-5487
        log_info("Expected Server Version: {}".format(expected_server_version))
        log_info("Running Server Version: {}".format(running_server_version))
        if running_server_version != expected_server_version:
            raise ProvisioningError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version))
    elif len(expected_server_version_parts) == 1:
        # 4.1.1
        running_server_version_parts = running_server_version.split("-")
        log_info("Expected Server Version: {}".format(expected_server_version))
        log_info("Running Server Version: {}".format(running_server_version_parts[0]))
        if expected_server_version != running_server_version_parts[0]:
            raise ProvisioningError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version_parts[0]))
    else:
        raise ProvisioningError("Unsupported version format")


class CouchbaseServer:
    """ Installs Couchbase Server on machine host"""

    def __init__(self, url):
        self.url = url

        # Strip http prefix and port to store host
        host = self.url.replace("http://", "")
        host = host.replace(":8091", "")
        self.host = host
        self.remote_executor = RemoteExecutor(self.host)

        self._session = Session()
        self._session.auth = ("Administrator", "password")

    def delete_bucket(self, name):
        """ Delete a Couchbase Server bucket with the given 'name' """
        resp = self._session.delete("{0}/pools/default/buckets/{1}".format(self.url, name))
        log_r(resp)
        resp.raise_for_status()

    def delete_buckets(self):
        count = 0
        while True:

            if count > 3:
                raise CBServerError("Max retries for bucket creation hit. Could not delete buckets!")

            resp = self._session.get("{}/pools/default/buckets".format(self.url))
            log_r(resp)
            resp.raise_for_status()

            obj = json.loads(resp.text)

            existing_bucket_names = []
            for entry in obj:
                existing_bucket_names.append(entry["name"])

            if len(existing_bucket_names) == 0:
                # No buckets to delete. Exit loop
                break

            log_info("Existing buckets: {}".format(existing_bucket_names))
            log_info("Deleting buckets: {}".format(existing_bucket_names))

            # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
            # Delete existing buckets
            num_failures = 0
            for bucket_name in existing_bucket_names:
                try:
                    self.delete_bucket(bucket_name)
                except HTTPError:
                    num_failures += 1
                    log_info("Failed to delete bucket. Retrying ...")

            # A 500 error may have occured, query for buckets and try to delete them again
            if num_failures > 0:
                time.sleep(5)
                count += 1
            else:
                # All bucket deletions were successful
                break

    def wait_for_ready_state(self):
        """
        Verify all server node is in are in a "healthy" state to avoid sync_gateway startup failures
        Work around for this - https://github.com/couchbase/sync_gateway/issues/1745
        """
        start = time.time()
        while True:

            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            # Verfy the server is in a "healthy", not "warmup" state
            try:
                resp = self._session.get("{}/pools/nodes".format(self.url))
                log_r(resp)
            except ConnectionError:
                # If bringing a server online, there may be some connnection issues. Continue and try again.
                time.sleep(1)
                continue

            resp_obj = resp.json()

            all_nodes_healthy = True
            for node in resp_obj["nodes"]:
                if node["status"] != "healthy":
                    all_nodes_healthy = False
                    log_info("Node is still not healthy. Status: {} Retrying ...".format(node["status"]))
                    time.sleep(1)

            if not all_nodes_healthy:
                continue

            log_info("All nodes are healthy")
            log_debug(resp_obj)
            # All nodes are heathy if it made it to here
            break

    def get_available_ram(self):
        """
        Call the Couchbase REST API to get the total memory available on the machine
        """
        resp = self._session.get("{}/pools/default".format(self.url))
        resp.raise_for_status()
        resp_json = resp.json()

        # Workaround for https://github.com/couchbaselabs/mobile-testkit/issues/709
        # where some node report mem_total = 0. Loop over all the nodes and find highest val
        mem_total_highest = 0
        for node in resp_json["nodes"]:
            mem_total = node["systemStats"]["mem_total"]
            if mem_total > mem_total_highest:
                mem_total_highest = mem_total
        return mem_total_highest

    def create_buckets(self, bucket_names):
        """
        # Figure out what total ram available is
        # Divide by number of buckets
        """
        if len(bucket_names) == 0:
            return
        log_info("Creating buckets: {}".format(bucket_names))
        ram_multiplier = 0.80
        total_avail_ram_bytes = self.get_available_ram()
        total_avail_ram_mb = int(total_avail_ram_bytes / (1024 * 1024))
        n1ql_indexer_ram_mb = 512
        effective_avail_ram_mb = int(total_avail_ram_mb * ram_multiplier) - n1ql_indexer_ram_mb
        per_bucket_ram_mb = int(effective_avail_ram_mb / len(bucket_names))
        log_info("total_avail_ram_mb: {} effective_avail_ram_mb: {} effective_avail_ram_mb: {}".format(total_avail_ram_mb, effective_avail_ram_mb, effective_avail_ram_mb))
        for bucket_name in bucket_names:
            log_info("Create bucket {} with per_bucket_ram_mb {}".format(bucket_name, per_bucket_ram_mb))
            self.create_bucket(bucket_name, per_bucket_ram_mb)

    def create_bucket(self, name, ramQuotaMB=1024):
        """
        1. Create CBS bucket via REST
        2. Create client connection and poll until bucket is available
           Catch all connection exception and break when KeyNotFound error is thrown
        3. Verify all server nodes are in a 'healthy' state before proceeding

        Followed the docs below that suggested this approach.
        http://docs.couchbase.com/admin/admin/REST/rest-bucket-create.html
        """

        log_info("Creating bucket {} with RAM {}".format(name, ramQuotaMB))

        data = {
            "name": name,
            "ramQuotaMB": str(ramQuotaMB),
            "authType": "sasl",
            "proxyPort": "11211",
            "bucketType": "couchbase",
            "flushEnabled": "1"
        }

        resp = self._session.post("{}/pools/default/buckets".format(self.url), data=data)
        log_r(resp)
        resp.raise_for_status()

        # Create client an retry until KeyNotFound error is thrown
        start = time.time()
        while True:

            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise Exception("TIMEOUT while trying to create server buckets.")
            try:
                bucket = Bucket("couchbase://{}/{}".format(self.host, name))
                bucket.get('foo')
            except ProtocolError:
                log_info("Client Connection failed: Retrying ...")
                time.sleep(1)
                continue
            except TemporaryFailError:
                log_info("Failure from server: Retrying ...")
                time.sleep(1)
                continue
            except NotFoundError:
                log_info("Key not found error: Bucket is ready!")
                break

        self.wait_for_ready_state()

        return name

    def delete_couchbase_server_cached_rev_bodies(self, bucket):
        """
        Deletes docs that follow the below format
        _sync:rev:att_doc:34:1-e7fa9a5e6bb25f7a40f36297247ca93e
        """

        b = Bucket("couchbase://{}/{}".format(self.host, bucket))

        cached_rev_doc_ids = []
        b.n1ql_query("CREATE PRIMARY INDEX ON `{}`".format(bucket)).execute()
        for row in b.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket, bucket)):
            if row["$1"]["id"].startswith("_sync:rev"):
                cached_rev_doc_ids.append(row["$1"]["id"])

        log_info("Found temp rev docs: {}".format(cached_rev_doc_ids))
        for doc_id in cached_rev_doc_ids:
            log_debug("Removing: {}".format(doc_id))
            b.remove(doc_id)

    def get_server_docs_with_prefix(self, bucket, prefix):
        """
        Returns server doc ids matching a prefix (ex. '_sync:rev:')
        """

        b = Bucket("couchbase://{}/{}".format(self.host, bucket))

        found_ids = []
        b.n1ql_query("CREATE PRIMARY INDEX ON `{}`".format(bucket)).execute()
        for row in b.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket, bucket)):
            log_info(row)
            if row["$1"]["id"].startswith(prefix):
                found_ids.append(row["$1"]["id"])

        return found_ids

    def _get_tasks(self):
        """
        Returns the current tasks from the server
        """
        resp = self._session.get("{}/pools/default/tasks".format(self.url))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return resp_obj

    def _wait_for_rebalance_complete(self):
        """
        Polls couchbase server tasks endpoint for any running rebalances.
        Exits when no rebalances are in running state

        /pools/default/tasks format:
        [
            {
                "type": "rebalance",
                "status": "running",
                ...
            }
        ]
        """

        # Check that rebalance is in the tasks before polling for its completion
        start = time.time()
        found_rebalance = False
        while not found_rebalance:

            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise TimeoutError("Did not find rebalance task!")

            tasks = self._get_tasks()
            for task in tasks:
                if task["type"] == "rebalance":
                    log_info("Rebalance found in tasks!")
                    found_rebalance = True

            if not found_rebalance:
                log_info("Did not find rebalance task. Retrying.")
                time.sleep(1)

        start = time.time()
        while True:

            if time.time() - start > keywords.constants.REBALANCE_TIMEOUT_SECS:
                raise Exception("wait_for_rebalance_complete: TIMEOUT")

            tasks = self._get_tasks()

            done_rebalacing = True
            for task in tasks:
                # loop through each task and see if any rebalance tasks are running
                task_type = task["type"]
                task_status = task["status"]
                log_info("{} is {}".format(task_type, task_status))
                if task_type == "rebalance" and task_status == "running":
                    done_rebalacing = False

            if done_rebalacing:
                break

            time.sleep(1)

    def add_node(self, server_to_add):
        """
        Add the server_to_add to a Couchbase Server cluster
        """

        if not isinstance(server_to_add, CouchbaseServer):
            raise TypeError("'server_to_add' must be a 'CouchbaseServer'")

        log_info("Adding server node {} to cluster ...".format(server_to_add))
        data = "hostname={}&user=Administrator&password=password&services=kv".format(
            server_to_add.host
        )

        # HACK: Retry below addresses the following problem:
        #  1. Rebalance a node out
        #  2. Try to to immediately add node back into the cluster
        #  3. Fails because node is in state where it can't be add in yet
        # To work around this:
        #  1. Retry / wait until add node POST command is successful
        start = time.time()
        while True:

            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise Exception("wait_for_rebalance_complete: TIMEOUT")

            # Override session headers for this one off request
            resp = self._session.post(
                "{}/controller/addNode".format(self.url),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data
            )

            log_r(resp)

            # If status of the POST is not 200, retry the request after a second
            if resp.status_code == 200:
                log_info("{} added to cluster successfully".format(server_to_add))
                break
            else:
                log_info("{}: Could not add {} to cluster. Retrying ...".format(resp.status_code, server_to_add))
                time.sleep(1)

    def rebalance_out(self, cluster_servers, server_to_remove):
        """
        Issues a call to the admin_serve to remove a server from a pool.
        Then wait for rebalance to complete.
        """
        if not isinstance(server_to_remove, CouchbaseServer):
            raise TypeError("'server_to_remove' must be a 'CouchbaseServer'")

        # Add all servers except server_to_add to known nodes
        known_nodes = "knownNodes="
        for server in cluster_servers:
            server = server.replace("http://", "")
            server = server.replace(":8091", "")
            known_nodes += "ns_1@{},".format(server)

        # Add server_to_add to known nodes
        ejected_node = "ejectedNodes=ns_1@{}".format(server_to_remove.host)
        data = "{}&{}".format(ejected_node, known_nodes)

        log_info("Starting rebalance out: {} with nodes {}".format(server_to_remove.host, data))
        # Override session headers for this one off request
        resp = self._session.post(
            "{}/controller/rebalance".format(self.url),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data
        )
        log_r(resp)
        resp.raise_for_status()

        self._wait_for_rebalance_complete()

        return True

    def rebalance_in(self, cluster_servers, server_to_add):
        """
        Adds a server from a pool and waits for rebalance to complete.
        cluster_servers should be a list of endpoints running Couchbase server.
            ex. ["http:192.168.33.10:8091", "http:192.168.33.11:8091", ...]
        """

        if not isinstance(server_to_add, CouchbaseServer):
            raise TypeError("'server_to_add' must be a 'CouchbaseServer'")

        # Add all servers except server_to_add to known nodes
        known_nodes = "knownNodes="
        for server in cluster_servers:
            server = server.replace("http://", "")
            server = server.replace(":8091", "")

            if server_to_add.host != server:
                known_nodes += "ns_1@{},".format(server)

        # Add server_to_add to known nodes
        data = "{}ns_1@{}".format(known_nodes, server_to_add.host)

        # Rebalance nodes
        log_info("Starting rebalance in for {}".format(server_to_add))
        log_info("Known nodes: {}".format(data))

        # Override session headers for this one off request
        resp = self._session.post(
            "{}/controller/rebalance".format(self.url),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data
        )
        log_r(resp)
        resp.raise_for_status()

        self._wait_for_rebalance_complete()

        return True

    def recover(self, server_to_recover):

        if not isinstance(server_to_recover, CouchbaseServer):
            raise TypeError("'server_to_add' must be a 'CouchbaseServer'")

        log_info("Setting recover mode to 'delta' for server {}".format(server_to_recover.host))
        data = "otpNode=ns_1@{}&recoveryType=delta".format(server_to_recover.host)
        # Override session headers for this one off request
        resp = self._session.post(
            "{}/controller/setRecoveryType".format(self.url),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data
        )

        log_r(resp)
        resp.raise_for_status()

        # TODO reset Quota

    def start(self):
        """Starts a running Couchbase Server via 'service couchbase-server start'"""

        command = "sudo service couchbase-server start"
        self.remote_executor.must_execute(command)
        self.wait_for_ready_state()

    def _verify_stopped(self):
        """Polls until the server url is unreachable"""

        start = time.time()
        while True:
            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise TimeoutError("Waiting for server to be unreachable but it never was!")
            try:
                resp = self._session.get("{}/pools".format(self.url))
                log_r(resp)
                resp.raise_for_status()
            except ConnectionError:
                # This is expected and used to determine if a server node has gone offline
                break

            except HTTPError as e:
                # 500 errors may happen as a result of the node going down
                log_error(e)
                continue

            time.sleep(1)

    def stop(self):
        """Stops a running Couchbase Server via 'service couchbase-server stop'"""

        command = "sudo service couchbase-server stop"
        self.remote_executor.must_execute(command)
        self._verify_stopped()
