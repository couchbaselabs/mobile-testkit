import time
import json
import requests
from requests.exceptions import ConnectionError, HTTPError
from requests import Session
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from libraries.provision.ansible_runner import AnsibleRunner

from couchbase.bucket import Bucket
from couchbase.exceptions import CouchbaseError, NotFoundError

import keywords.constants
from keywords.remoteexecutor import RemoteExecutor
from keywords.exceptions import CBServerError, ProvisioningError, TimeoutError, RBACUserCreationError, RBACUserDeletionError
from keywords.utils import log_r, log_info, log_debug, log_error, hostname_for_url
from keywords import types

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def get_server_version(host, cbs_ssl=False):
    """ Gets the server version in the format '4.1.1-5487' for a running Couchbase Server"""

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
    """ Verifies that the version of a running Couchbase Server is the 'expected_server_version' """

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

        error_count = 0
        max_retries = 5

        # Retry to avoid intermittent Connection issues when getting buckets
        while True:
            if error_count == max_retries:
                raise CBServerError("Error! Could not get buckets after retries.")
            try:
                resp = self._session.get("{}/pools/default/buckets".format(self.url))
                log_r(resp)
                resp.raise_for_status()
                break
            except ConnectionError:
                log_info("Hit a ConnectionError while trying to get buckets. Retrying ...")
                error_count += 1
                time.sleep(1)

        obj = json.loads(resp.text)

        for entry in obj:
            bucket_names.append(entry["name"])

        log_info("Found buckets: {}".format(bucket_names))
        return bucket_names

    def delete_bucket(self, name):
        """ Delete a Couchbase Server bucket with the given 'name' """
        server_version = get_server_version(self.host, self.cbs_ssl)
        server_major_version = int(server_version.split(".")[0])

        if server_major_version >= 5:
            self._delete_internal_rbac_bucket_user(name)

        resp = self._session.delete("{0}/pools/default/buckets/{1}".format(self.url, name))
        log_r(resp)
        resp.raise_for_status()

    def delete_buckets(self):
        """ Deletes all of the buckets on a Couchbase Server.
        If the buckets cannot be deleted after 3 tries, an exception will be raised.
        """

        count = 0
        max_retries = 3
        while True:

            if count == max_retries:
                raise CBServerError("Max retries for bucket creation hit. Could not delete buckets!")

            # Get a list of the bucket names
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
                except HTTPError as e:
                    num_failures += 1
                    log_info("Failed to delete bucket: {}. Retrying ...".format(e))
                except ConnectionError as ce:
                    num_failures += 1
                    log_info("Failed to delete bucket: {} Retrying ...".format(ce))

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

            elapsed = time.time()
            if elapsed - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
                raise Exception("Timeout: Server not in ready state! {}s".format(elapsed))

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

    def _create_internal_rbac_bucket_user(self, bucketname):
        # Create user with username=bucketname and assign role
        # bucket_admin and cluster_admin
        roles = "ro_admin,bucket_full_access[{}]".format(bucketname)
        password = 'password'

        data_user_params = {
            "name": bucketname,
            "roles": roles,
            "password": password
        }

        log_info("Creating RBAC user {} with password {} and roles {}".format(bucketname, password, roles))

        rbac_url = "{}/settings/rbac/users/local/{}".format(self.url, bucketname)

        resp = None
        try:
            resp = self._session.put(rbac_url, data=data_user_params, auth=('Administrator', 'password'))
            log_r(resp)
            resp.raise_for_status()
        except HTTPError as h:
            log_info("resp code: {}; error: {}".format(resp, h))
            raise RBACUserCreationError(h)

    def _delete_internal_rbac_bucket_user(self, bucketname):
        # Delete user with username=bucketname
        data_user_params = {
            "name": bucketname
        }

        log_info("Deleting RBAC user {}".format(bucketname))

        rbac_url = "{}/settings/rbac/users/local/{}".format(self.url, bucketname)

        resp = None
        try:
            resp = self._session.delete(rbac_url, data=data_user_params, auth=('Administrator', 'password'))
            log_r(resp)
            resp.raise_for_status()
        except HTTPError as h:
            log_info("resp code: {}; error: {}".format(resp, h))
            if '404 Client Error: Object Not Found for url' in h.message:
                log_info("RBAC user does not exist, no need to delete RBAC bucket user {}".format(bucketname))
            else:
                raise RBACUserDeletionError(h)

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
            "flushEnabled": "1",
            "replicaNumber": 0
        }

        if server_major_version <= 4:
            # Create a bucket with password for server_major_version < 5
            # proxyPort should not be passed for 5.0.0 onwards for bucket creation
            data["saslPassword"] = "password"
            data["proxyPort"] = "11211"

        resp = None
        try:
            resp = self._session.post("{}/pools/default/buckets".format(self.url), data=data)
            log_r(resp)
            resp.raise_for_status()
        except HTTPError as h:
            log_info("resp code: {}; resp text: {}; error: {}".format(resp, resp.json(), h))
            raise

        # Create a user with username=bucketname
        if server_major_version >= 5:
            self._create_internal_rbac_bucket_user(name)

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
        b_manager = b.bucket_manager()
        b_manager.n1ql_index_create_primary(ignore_exists=True)
        cached_rev_doc_ids = []
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
        b_manager = b.bucket_manager()
        b_manager.n1ql_index_create_primary(ignore_exists=True)
        found_ids = []
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

            time.sleep(5)

    def add_node(self, server_to_add, services="kv"):
        """
        Add the server_to_add to a Couchbase Server cluster
        """

        if not isinstance(server_to_add, CouchbaseServer):
            raise TypeError("'server_to_add' must be a 'CouchbaseServer'")

        log_info("Adding server node {} to cluster ...".format(server_to_add.host))
        data = "hostname={}&user=Administrator&password=password&services={}".format(
            server_to_add.host, services
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
                log_info("{} added to cluster successfully".format(server_to_add.host))
                break
            else:
                log_info("{}: {}: Could not add {} to cluster. Retrying ...".format(resp.status_code, resp.json(), server_to_add.host))
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

        # Add server_to_remove to ejected_node
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
        log_info("Starting rebalance in for {}".format(server_to_add.host))
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

    def delete_vbucket(self, vbucket_number, bucket_name):
        """ Deletes a vbucket file for a number and bucket"""

        vbucket_filename = "{}.couch.1".format(vbucket_number)

        # Delete some vBucket file to start a server rollback
        # Example vbucket files - 195.couch.1  310.couch.1  427.couch.1  543.couch.1
        log_info("Deleting vBucket file '66.couch.1'")
        self.remote_executor.must_execute('sudo find /opt/couchbase/var/lib/couchbase/data/data-bucket -name "{}" -delete'.format(vbucket_filename))
        log_info("Listing vBucket files ...")
        out, err = self.remote_executor.must_execute("sudo ls /opt/couchbase/var/lib/couchbase/data/{}/".format(bucket_name))

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

    def get_sdk_bucket(self, bucket_name):
        """ Gets an SDK bucket object """
        connection_str = "couchbase://{}/{}".format(self.host, bucket_name)
        return Bucket(connection_str, password='password')

    def get_package_name(self, version, build_number, cbs_platform="centos7"):
        """
        Given:

        version - the version without any build number information, eg 4.5.0
        build_number - the build number associated with this major version release, eg, 2601 (or None)

        Return the filename portion of the package download URL

        """

        if version.startswith("3.1.6"):
            return "couchbase-server-enterprise-{}-{}.x86_64.rpm".format(version, cbs_platform)
        elif version.startswith("3.1"):
            return "couchbase-server-enterprise_{}_x86_64_{}-{}-rel.rpm".format(cbs_platform, version, build_number)
        else:
            return "couchbase-server-enterprise-{}-{}-{}.x86_64.rpm".format(version, build_number, cbs_platform)

    def resolve_cb_nas_url(self, version, build_number, cbs_platform="centos7"):
        """
        Resolve a download URL for couchbase server on the internal VPN download site

        Given:

        version - the version without any build number information, eg 4.5.0
        build_number - the build number associated with this major version release, eg, 2601 (or None)

        Return the base_url of the package download URL (everything except the filename)

        """

        cbnas_base_url = "http://latestbuilds.service.couchbase.com/builds/latestbuilds/couchbase-server"

        if version.startswith("3.1"):
            base_url = "http://latestbuilds.service.couchbase.com/"
        elif version.startswith("4.0") or version.startswith("4.1"):
            base_url = "{}/sherlock/{}".format(cbnas_base_url, build_number)
        elif version.startswith("4.5") or version.startswith("4.6"):
            base_url = "{}/watson/{}".format(cbnas_base_url, build_number)
        elif version.startswith("4.7") or version.startswith("5.0"):
            base_url = "{}/spock/{}".format(cbnas_base_url, build_number)
        elif version.startswith("5.1"):
            base_url = "{}/vulcan/{}".format(cbnas_base_url, build_number)
        else:
            raise Exception("Unexpected couchbase server version: {}".format(version))

        package_name = self.get_package_name(version, build_number, cbs_platform)
        return base_url, package_name

    def resolve_cb_mobile_url(self, version, cbs_platform="centos7"):
        """
        Resolve a download URL for the corresponding package to given
        version on http://cbmobile-packages.s3.amazonaws.com (an S3 bucket
        for couchbase mobile that mirrors released couchbase server versions)

        Given:

        version - the version without any build number information, eg 4.5.0

        Return the base_url of the package download URL (everything except the filename)

        """
        released_versions = {
            "5.0.0": "3519",
            "4.6.3": "4136",
            "4.6.2": "3905",
            "4.6.1": "3652",
            "4.6.0": "3573",
            "4.5.1": "2844",
            "4.5.0": "2601",
            "4.1.2": "6088",
            "4.1.1": "5914",
            "4.1.0": "5005",
            "4.0.0": "4051",
            "3.1.5": "1859",
            "3.1.6": "1904"
        }
        build_number = released_versions[version]
        base_url = "http://cbmobile-packages.s3.amazonaws.com"
        package_name = self.get_package_name(version, build_number, cbs_platform)
        return base_url, package_name

    def upgrade_server(self, cluster_config, server_version_build, cbs_platform, target=None, toy_build=None):
        ansible_runner = AnsibleRunner(cluster_config)

        log_info(">>> Upgrading Couchbase Server")
        # Install Server
        if toy_build:
            # http://server.jenkins.couchbase.com/view/All/job/watson-toy/1770/artifact/couchbase-server-enterprise-5.0.0-9900-centos7.x86_64.rpm
            toy_build_url_parts = toy_build.split('/')
            toy_build_url_len = len(toy_build_url_parts)
            server_package_name = toy_build_url_parts[-1]
            server_baseurl = "/".join(toy_build_url_parts[0:(toy_build_url_len - 1)])
        else:
            version_build = server_version_build.split("-")
            server_verion = version_build[0]
            if len(version_build) == 2:
                # Build number is included
                server_build = version_build[1]
            else:
                server_build = None

            if server_build is None:
                server_baseurl, server_package_name = self.resolve_cb_mobile_url(server_verion, cbs_platform)
            else:
                server_baseurl, server_package_name = self.resolve_cb_nas_url(server_verion, server_build, cbs_platform)

        if target is not None:
            target = hostname_for_url(cluster_config, target)
            log_info("Upgrading Couchbase server on {} ...".format(target))
            status = ansible_runner.run_ansible_playbook(
                "upgrade-couchbase-server-package.yml",
                subset=target,
                extra_vars={
                    "couchbase_server_package_base_url": server_baseurl,
                    "couchbase_server_package_name": server_package_name
                }
            )
        else:
            log_info("Upgrading Couchbase server on all nodes")
            status = ansible_runner.run_ansible_playbook(
                "upgrade-couchbase-server-package.yml",
                extra_vars={
                    "couchbase_server_package_base_url": server_baseurl,
                    "couchbase_server_package_name": server_package_name
                }
            )

        if status != 0:
            raise ProvisioningError("Failed to install Couchbase Server")

        self.wait_for_ready_state()
