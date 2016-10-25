import requests
import time
import json

from couchbase.bucket import Bucket
from couchbase.exceptions import ProtocolError
from couchbase.exceptions import TemporaryFailError
from couchbase.exceptions import NotFoundError

from keywords.constants import CLIENT_REQUEST_TIMEOUT
from keywords.constants import REBALANCE_TIMEOUT
from keywords.exceptions import CBServerError
from keywords.exceptions import ProvisioningError
from keywords.utils import log_r
from keywords.utils import log_info
from keywords.utils import log_debug


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
        raise ValueError("Unsupported version format")


class CouchbaseServer:
    """ Installs Couchbase Server on machine host"""

    def __init__(self, url):
        self._headers = {"Content-Type": "application/json"}
        self._auth = ("Administrator", "password")
        self.url = url

    def delete_buckets(self):
        count = 0
        while count < 3:
            resp = requests.get("{}/pools/default/buckets".format(self.url), auth=self._auth, headers=self._headers)
            log_r(resp)
            resp.raise_for_status()

            obj = json.loads(resp.text)

            existing_bucket_names = []
            for entry in obj:
                existing_bucket_names.append(entry["name"])

            log_info("Existing buckets: {}".format(existing_bucket_names))
            log_info("Deleting buckets: {}".format(existing_bucket_names))

            # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
            delete_num = 0
            # Delete existing buckets
            for bucket_name in existing_bucket_names:
                resp = requests.delete("{0}/pools/default/buckets/{1}".format(self.url, bucket_name), auth=self._auth, headers=self._headers)
                log_r(resp)
                if resp.status_code == 200:
                    delete_num += 1

            if delete_num == len(existing_bucket_names):
                break
            else:
                # A 500 error may have occured, query for buckets and try to delete them again
                time.sleep(5)
                count += 1

        # Check that max retries did not occur
        if count == 3:
            raise CBServerError("Max retries for bucket creation hit. Could not delete buckets!")

    def wait_for_ready_state(self):
        """
        Verify all server node is in are in a "healthy" state to avoid sync_gateway startup failures
        Work around for this - https://github.com/couchbase/sync_gateway/issues/1745
        """
        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            # Verfy the server is in a "healthy", not "warmup" state
            resp = requests.get("{}/pools/nodes".format(self.url), auth=self._auth, headers=self._headers)
            log_r(resp)

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
        resp = requests.get("{}/pools/default".format(self.url), auth=self._auth)
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

        resp = requests.post("{}/pools/default/buckets".format(self.url), auth=self._auth, data=data)
        log_r(resp)
        resp.raise_for_status()

        # Create client an retry until KeyNotFound error is thrown
        client_host = self.url.replace("http://", "")
        client_host = client_host.replace(":8091", "")
        log_info(client_host)

        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("TIMEOUT while trying to create server buckets.")
            try:
                bucket = Bucket("couchbase://{}/{}".format(client_host, name))
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
        client_host = self.replace("http://", "")
        client_host = client_host.replace(":8091", "")

        b = Bucket("couchbase://{}/{}".format(client_host, bucket))

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
        client_host = self.replace("http://", "")
        client_host = client_host.replace(":8091", "")

        b = Bucket("couchbase://{}/{}".format(client_host, bucket))

        found_ids = []
        b.n1ql_query("CREATE PRIMARY INDEX ON `{}`".format(bucket)).execute()
        for row in b.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket, bucket)):
            log_info(row)
            if row["$1"]["id"].startswith(prefix):
                found_ids.append(row["$1"]["id"])

        return found_ids

    def _wait_for_rebalance_complete(self, url):
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

        start = time.time()
        while True:

            if time.time() - start > REBALANCE_TIMEOUT:
                raise Exception("wait_for_rebalance_complete: TIMEOUT")

            resp = requests.get("{}/pools/default/tasks".format(url), auth=self._auth)
            log_r(resp)
            resp.raise_for_status()

            resp_obj = resp.json()

            done_rebalacing = True
            for task in resp_obj:
                # loop through each task and see if any rebalance tasks are running
                task_type = task["type"]
                task_status = task["status"]
                log_info("{} is {}".format(task_type, task_status))
                if task_type == "rebalance" and task_status == "running":
                    done_rebalacing = False

            if done_rebalacing:
                break;

            time.sleep(1)

    def _add_node(self, server_to_add):
        """
        Add the server_to_add to a Couchbase Server cluster
        admin_server format:    http://localhost:8091
        server_to_add format:   http://localhost:8091
        """

        server_to_add_stripped = server_to_add.replace("http://", "")
        server_to_add_stripped = server_to_add_stripped.replace(":8091", "")

        log_info("Adding server node {} to cluster ...".format(server_to_add))
        data = "hostname={}&user=Administrator&password=password&services=kv".format(
            server_to_add_stripped
        )

        # HACK: Retries added to handle the following scenario.
        # 1. A node has been rebalanced out of a cluster
        # 2. Try to rebalance the node back in immediately.
        # The node may not be in a ready state. There in no property exposed on the
        #   REST API to poll so a retry will have to do
        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("wait_for_rebalance_complete: TIMEOUT")

            resp = requests.post(
                "{}/controller/addNode".format(self.url),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=self._auth,
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

    def rebalance_out(self, server_to_remove):
        """
        Issues a call to the admin_serve to remove a server from a pool.
        Then wait for rebalance to complete.
        admin_server format:        http://localhost:8091
        server_to_remove format:    http://localhost:8091
        """

        admin_server_stripped = self.url.replace("http://", "")
        admin_server_stripped = admin_server_stripped.replace(":8091", "")

        server_to_remove_stripped = server_to_remove.replace("http://", "")
        server_to_remove_stripped = server_to_remove_stripped.replace(":8091", "")

        log_info("Starting rebalance out: {}".format(server_to_remove))
        data = "ejectedNodes=ns_1@{}&knownNodes=ns_1@{},ns_1@{}".format(
            server_to_remove_stripped,
            admin_server_stripped,
            server_to_remove_stripped
        )

        resp = requests.post(
            "{}/controller/rebalance".format(self.url),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=self._auth,
            data=data
        )
        log_r(resp)
        resp.raise_for_status()

        self._wait_for_rebalance_complete(self.url)

        return True

    def rebalance_in(self, server_to_add):
        """
        Adds a server from a pool and waits for rebalance to complete.
        admin_server format:    http://localhost:8091
        server_to_add format:   http://localhost:8091
        """

        admin_server_stripped = self.url.replace("http://", "")
        admin_server_stripped = admin_server_stripped.replace(":8091", "")

        server_to_add_stripped = server_to_add.replace("http://", "")
        server_to_add_stripped = server_to_add_stripped.replace(":8091", "")

        # Add node
        self._add_node(server_to_add)

        # Rebalance nodes
        log_info("Starting rebalance in: {}".format(server_to_add))
        data = "knownNodes=ns_1@{},ns_1@{}".format(
            admin_server_stripped,
            server_to_add_stripped
        )

        resp = requests.post(
            "{}/controller/rebalance".format(self.url),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=self._auth,
            data=data
        )
        log_r(resp)
        resp.raise_for_status()

        self._wait_for_rebalance_complete(self.url)

        return True

    def kill(self):
        pass

    def start(self):
        pass