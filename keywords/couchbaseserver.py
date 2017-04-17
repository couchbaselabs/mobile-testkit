import time
import json
import requests
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests import Session
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from couchbase.bucket import Bucket
from couchbase.exceptions import CouchbaseError
from couchbase.exceptions import NotFoundError


import keywords.constants
from keywords.remoteexecutor import RemoteExecutor
from keywords.exceptions import CBServerError
from keywords.exceptions import ProvisioningError
from keywords.exceptions import TimeoutError
from keywords.exceptions import RBACUserCreationError
from keywords.exceptions import RBACUserDeletionError
from keywords.utils import log_r
from keywords.utils import log_info
from keywords.utils import log_debug
from keywords.utils import log_error
from keywords import types

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def get_server_version(host, cbs_ssl=False):
    server_scheme = "http"
    server_port = 8091

    if cbs_ssl:
        server_scheme = "https"
        server_port = 18091

    resp = requests.get("{}://Administrator:password@{}:{}/pools".format(server_scheme, host, server_port), verify=False)
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    # Actual version is the following format 4.1.1-5914-enterprise
    running_server_version = resp_obj["implementationVersion"]
    running_server_version_parts = running_server_version.split("-")

    # Return version in the formatt 4.1.1-5487
    return "{}-{}".format(running_server_version_parts[0], running_server_version_parts[1])


def verify_server_version(host, expected_server_version, cbs_ssl=False):
    running_server_version = get_server_version(host, cbs_ssl=cbs_ssl)
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


def create_internal_rbac_bucket_user(url, bucketname):
    # Create user with username=bucketname and assign role
    # bucket_admin and cluster_admin
    roles = "cluster_admin,bucket_admin[{}]".format(bucketname)
    password = 'password'

    data_user_params = {
        "name": bucketname,
        "roles": roles,
        "password": password
    }

    log_info("Creating RBAC user {} with password {} and roles {}".format(bucketname, password, roles))

    rbac_url = "{}/settings/rbac/users/builtin/{}".format(url, bucketname)

    resp = ""
    try:
        resp = requests.put(rbac_url, data=data_user_params, auth=('Administrator', 'password'))
        log_r(resp)
        resp.raise_for_status()
    except HTTPError as h:
        log_info("resp code: {}; error: {}".format(resp, h))
        raise RBACUserCreationError(h)


def delete_internal_rbac_bucket_user(url, bucketname):
    # Delete user with username=bucketname
    data_user_params = {
        "name": bucketname
    }

    log_info("Deleting RBAC user {}".format(bucketname))

    rbac_url = "{}/settings/rbac/users/builtin/{}".format(url, bucketname)

    resp = ""
    try:
        resp = requests.delete(rbac_url, data=data_user_params, auth=('Administrator', 'password'))
        log_r(resp)
        resp.raise_for_status()
    except HTTPError as h:
        log_info("resp code: {}; error: {}".format(resp, h))
        raise RBACUserDeletionError(h)


class CouchbaseServer:
    """ Installs Couchbase Server on machine host"""

    def __init__(self, url):
        self.url = url
        self.cbs_ssl = False

        # Strip http prefix and port to store host
        if "https" in self.url:
            host = self.url.replace("https://", "")
            host = host.replace(":18091", "")
            self.cbs_ssl = True
        else:
            host = self.url.replace("http://", "")
            host = host.replace(":8091", "")

        self.host = host
        self.remote_executor = RemoteExecutor(self.host)

        self._session = Session()
        self._session.auth = ("Administrator", "password")

        if self.cbs_ssl:
            self._session.verify = False

    def get_bucket_names(self):
        """ Returns list of the bucket names for a given Couchbase Server."""

        bucket_names = []

        resp = self._session.get("{}/pools/default/buckets".format(self.url))
        log_r(resp)
        resp.raise_for_status()

        obj = json.loads(resp.text)

        for entry in obj:
            bucket_names.append(entry["name"])

        return bucket_names

    def delete_bucket(self, name):
        """ Delete a Couchbase Server bucket with the given 'name' """
        server_version = get_server_version(self.host, self.cbs_ssl)
        server_major_version = int(server_version.split(".")[0])

        resp = self._session.delete("{0}/pools/default/buckets/{1}".format(self.url, name))
        log_r(resp)
        resp.raise_for_status()
        if server_major_version >= 5:
            delete_internal_rbac_bucket_user(self.url, name)

    def delete_buckets(self):
        """ Deletes all of the buckets on a Couchbase Server.
        If the buckets cannot be deleted after 3 tries, an exception will be raised.
        """

        count = 0
        while True:

            if count > 3:
                raise CBServerError("Max retries for bucket creation hit. Could not delete buckets!")

            bucket_names = self.get_bucket_names()
            if len(bucket_names) == 0:
                # No buckets to delete. Exit loop
                break

            log_info("Existing buckets: {}".format(bucket_names))
            log_info("Deleting buckets: {}".format(bucket_names))

            # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
            # Delete existing buckets
            num_failures = 0
            for bucket_name in bucket_names:
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

        # Verify the buckets are gone
        bucket_names = self.get_bucket_names()
        if len(bucket_names) != 0:
            raise CBServerError("Failed to delete all of the server buckets!")

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

    def _get_mem_total_lowest(self, server_info):
        # Workaround for https://github.com/couchbaselabs/mobile-testkit/issues/709
        # Later updated for https://github.com/couchbaselabs/mobile-testkit/issues/1038
        # where some node report mem_total = 0. Loop over all the nodes and find the smallest non-zero val
        mem_total_lowest = None
        for node in server_info["nodes"]:
            mem_total = node["systemStats"]["mem_total"]
            if mem_total == 0:
                # ignore nodes that report mem_total = 0
                continue
            if mem_total_lowest is None:
                # no previous value for mem_total_lowest, use non-zero value we got back from node
                mem_total_lowest = mem_total
            elif mem_total < mem_total_lowest:
                # only use it if it's lower than previous low
                mem_total_lowest = mem_total

        if mem_total_lowest is None:
            raise ProvisioningError("All nodes reported 0MB of RAM available")

        return mem_total_lowest

    def _get_total_ram_mb(self):
        """
        Call the Couchbase REST API to get the total memory available on the machine. RAM returned is in mb
        """
        resp = self._session.get("{}/pools/default".format(self.url))
        resp.raise_for_status()
        resp_json = resp.json()

        mem_total_lowest = self._get_mem_total_lowest(resp_json)

        total_avail_ram_mb = int(mem_total_lowest / (1024 * 1024))
        log_info("total_avail_ram_mb: {}".format(total_avail_ram_mb))
        return total_avail_ram_mb

    def _get_effective_ram_mb(self):
        """ Return the amount of effective RAM ((total RAM * muliplier) - n1ql ram allocation)
        Given a total amount of ram
        """

        # Leave 20% of RAM available for the underlying OS
        ram_multiplier = 0.80

        # Needed for N1QL indexing overhead. This enables us to use N1QL in the Couchbase
        # python SDK for direct validation in Couchbase server in some of the functional tests
        n1ql_indexer_ram_mb = 512

        total_ram_mb = self._get_total_ram_mb()
        effective_avail_ram_mb = int(total_ram_mb * ram_multiplier) - n1ql_indexer_ram_mb

        log_info("effective_avail_ram_mb: {}".format(effective_avail_ram_mb))
        return effective_avail_ram_mb

    def get_ram_per_bucket(self, num_buckets):
        """ Returns the amount of ram allocated to each bucket for a given number of buckets"""

        effective_ram_mb = self._get_effective_ram_mb()
        ram_per_bucket_mb = int(effective_ram_mb / num_buckets)
        return ram_per_bucket_mb

    def create_buckets(self, bucket_names):
        """
        # Figure out what total ram available is
        # Divide by number of buckets
        """
        types.verify_is_list(bucket_names)

        if len(bucket_names) == 0:
            return
        log_info("Creating buckets: {}".format(bucket_names))

        # Get the amount of RAM to allocate for each server bucket
        per_bucket_ram_mb = self.get_ram_per_bucket(len(bucket_names))

        for bucket_name in bucket_names:
            self.create_bucket(bucket_name, per_bucket_ram_mb)

    def create_bucket(self, name, ram_quota_mb=1024):
        """
        1. Create CBS bucket via REST
        2. Create client connection and poll until bucket is available
           Catch all connection exception and break when KeyNotFound error is thrown
        3. Verify all server nodes are in a 'healthy' state before proceeding

        Followed the docs below that suggested this approach.
        http://docs.couchbase.com/admin/admin/REST/rest-bucket-create.html
        """

        log_info("Creating bucket {} with RAM {}".format(name, ram_quota_mb))

        server_version = get_server_version(self.host, self.cbs_ssl)
        server_major_version = int(server_version.split(".")[0])

        data = {
            "name": name,
            "ramQuotaMB": str(ram_quota_mb),
            "authType": "sasl",
            "bucketType": "couchbase",
            "flushEnabled": "1"
        }

        if server_major_version <= 4:
            # Create a bucket with password for server_major_version < 5
            # proxyPort should not be passed for 5.0.0 onwards for bucket creation
            data["saslPassword"] = "password"
            data["proxyPort"] = "11211"

        resp = ""
        try:
            resp = self._session.post("{}/pools/default/buckets".format(self.url), data=data)
            log_r(resp)
            resp.raise_for_status()
        except HTTPError as h:
            log_info("resp code: {}; resp text: {}; error: {}".format(resp, resp.json(), h))
            raise

        # Create a user with username=bucketname
        if server_major_version >= 5:
            create_internal_rbac_bucket_user(self.url, name)

        # Create client an retry until KeyNotFound error is thrown
        start = time.time()
        while True:

            if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise Exception("TIMEOUT while trying to create server buckets.")
            try:
                bucket = Bucket("couchbase://{}/{}".format(self.host, name), password='password')
                bucket.get('foo')
            except NotFoundError:
                log_info("Key not found error: Bucket is ready!")
                break
            except CouchbaseError as e:
                log_info("Error from server: {}, Retrying ...". format(e))
                time.sleep(1)
                continue

        self.wait_for_ready_state()

        return name

    def delete_couchbase_server_cached_rev_bodies(self, bucket):
        """
        Deletes docs that follow the below format
        _sync:rev:att_doc:34:1-e7fa9a5e6bb25f7a40f36297247ca93e
        """
        b = Bucket("couchbase://{}/{}".format(self.host, bucket), password='password')

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

        b = Bucket("couchbase://{}/{}".format(self.host, bucket), password='password')

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
            if "https" in server:
                server = server.replace("https://", "")
                server = server.replace(":18091", "")
            else:
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
            if "https" in server:
                server = server.replace("https://", "")
                server = server.replace(":18091", "")
            else:
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
        """Starts a running Couchbase Server via 'systemctl start couchbase-server'"""

        command = "systemctl start couchbase-server"
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
        """Stops a running Couchbase Server via 'systemctl stop couchbase-server'"""

        command = "systemctl stop couchbase-server"
        self.remote_executor.must_execute(command)
        self._verify_stopped()

    def delete_vbucket(self, vbucket_number, bucket_name):
        """ Deletes a vbucket file for a number and bucket"""

        vbucket_filename = "{}.couch.1".format(vbucket_number)

        # Delete some vBucket file to start a server rollback
        # Example vbucket files - 195.couch.1  310.couch.1  427.couch.1  543.couch.1
        log_info("Deleting vBucket file '66.couch.1'")
        self.remote_executor.must_execute('find /opt/couchbase/var/lib/couchbase/data/data-bucket -name "{}" -delete'.format(vbucket_filename))
        log_info("Listing vBucket files ...")
        out, err = self.remote_executor.must_execute("ls /opt/couchbase/var/lib/couchbase/data/{}/".format(bucket_name))

        # out format: [u'0.couch.1     264.couch.1  44.couch.1\t635.couch.1  820.couch.1\r\n',
        # u'1000.couch.1  265.couch.1 ...]
        vbucket_files = []
        for entry in out:
            vbucket_files.extend(entry.split())

        # Verify that the vBucket files starting with 5 are all gone
        log_info("Verifing vBucket files are deleted ...")

        # Try to catch potential silent failures from the remote executor
        if len(vbucket_files) < 1:
            raise CBServerError("No vbucket files found on server!")

        # Verify vbucket file no longer exists
        if vbucket_filename in vbucket_files:
            raise CBServerError("Found vbucket file: {}! This should have been removed")

    def restart(self):
        """ Restarts a couchbase server """
        self.remote_executor.must_execute("sudo systemctl restart couchbase-server")
