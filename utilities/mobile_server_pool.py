import sys
from datetime import timedelta
import paramiko
import time
from requests import Session
from optparse import OptionParser
from couchbase.cluster import PasswordAuthenticator, ClusterTimeoutOptions, ClusterOptions, Cluster
from keywords.utils import log_info
from couchbase.exceptions import CouchbaseException

SERVER_IP = "172.23.104.162"
USERNAME = 'Administrator'
PASSWORD = 'esabhcuoc'
BUCKET_NAME = "QE-mobile-pool"
SSH_NUM_RETRIES = 3
SSH_USERNAME = 'root'
SSH_PASSWORD = 'couchbase'
SSH_POLL_INTERVAL = 20

timeout_options = ClusterTimeoutOptions(kv_timeout=timedelta(seconds=5), query_timeout=timedelta(seconds=10))
options = ClusterOptions(PasswordAuthenticator(USERNAME, PASSWORD), timeout_options=timeout_options)
cluster = Cluster('couchbase://{}'.format(SERVER_IP), options)
sdk_client = cluster.bucket(BUCKET_NAME)


def get_nodes_available_from_mobile_pool(nodes_os_type, node_os_version):
    """
    Get number of nodes available
    :param num_of_nodes: No. of nodes one needs
    :param nodes_os_type: Type of OS for reserve node
    :param node_os_version: Version of OS for reserve node
    :param job_name_requesting_node: Name of the job requesting for node
    :return: list of nodes reserved
    """
    # Getting list of available nodes through n1ql query
    query_str = "select count(*) from `{}` where os='{}' " \
                "AND os_version='{}' AND state='available'".format(BUCKET_NAME, nodes_os_type, node_os_version)
    query = cluster.query(query_str)
    for row in query:
        count = row["$1"]
    print(count)


def get_nodes_from_pool_server(num_of_nodes, nodes_os_type, node_os_version, job_name_requesting_node):
    """
    Reserve no. of nodes from QE-mobile-pool
    :param num_of_nodes: No. of nodes one needs
    :param nodes_os_type: Type of OS for reserve node
    :param node_os_version: Version of OS for reserve node
    :param job_name_requesting_node: Name of the job requesting for node
    :return: list of nodes reserved
    """
    # Getting list of available nodes through n1ql query
    query_str = "select meta().id from `{}` where os='{}' " \
                "AND os_version='{}' AND state='available'".format(BUCKET_NAME, nodes_os_type, node_os_version)
    query = cluster.query(query_str)
    pool_list = []
    for row in query:
        doc_id = row["id"]
        print(doc_id, "doc id")
        is_node_reserved = reserve_node(doc_id, job_name_requesting_node)
        vm_alive = check_vm_alive(doc_id)
        if not vm_alive:
            query_str = "update `{}` set state=\"VM_NOT_ALLIVE\" where meta().id='{}' " \
                "and state='available'".format(doc_id)
            query = cluster.query(query_str)
        if is_node_reserved and vm_alive:
            pool_list.append(str(doc_id))

        if len(pool_list) == int(num_of_nodes):
            return pool_list

    # Not able to allocate all the requested nodes, hence release the node back to the pool
    release_node(pool_list, job_name_requesting_node)
    raise Exception("Not enough free node/s available to satisfy the request")


def check_vm_alive(server):
    num_retries = 0
    while num_retries <= SSH_NUM_RETRIES:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=server, username=SSH_USERNAME, password=SSH_PASSWORD)
            print("Successfully established test ssh connection to {0}. VM is recognized as valid.".format(server))
            return True
        except Exception as e:
            print("Exception occured while trying to establish ssh connection with {0}: {1}".format(server, str(e)))
            num_retries = num_retries + 1
            time.sleep(SSH_POLL_INTERVAL)
            continue

def reserve_node(doc_id, job_name, counter=0):
    """
    Reserve a node for a given job
    :param doc_id: Node name to be reserved
    :param job_name: Name of the job which is requesting for node
    :param counter: For recursion, passed by code itself
    :return: Bool
    """
    result = sdk_client.get(doc_id)
    doc = result.value
    curr_cas = result.cas
    # Reserving the ip from the pool and updating the entry in the bucket
    doc["prevUser"] = doc["username"]
    doc["username"] = job_name
    doc["state"] = "booked"
    try:
        sdk_client.replace(doc_id, doc, cas=curr_cas)
        return True
    except CouchbaseException as err:
        result = sdk_client.get(doc_id)
        doc = result.value
        if doc["state"] != "booked" and counter < 5:
            log_info("Attempt to reserve node {} failed due to error {}".format(doc_id, err))
            log_info("Re-try attempt no. {}".format(counter))
            return reserve_node(doc_id, job_name, counter + 1)
        else:
            log_info("Node has been booked by job {}".format(doc["username"]))
            log_info("Checking for other node")
            return False
    except Exception as err:
        log_info("Exception occurred: {}".format(err))
        return False


def release_node(pool_list, job_name):
    """
    Release all node given in pool list
    :param pool_list:  List of nodes to be released
    :param job_name:  Name of Jenkins job which has reserved the node
    :return: void
    """
    for node in pool_list:
        result = sdk_client.get(node)
        print(result.value)
        doc = result.value
        print(doc, "Doc details")
        if doc["username"] == job_name:
            doc["prevUser"] = doc["username"]
            doc["username"] = ""
            doc["state"] = "available"
            sdk_client.replace(node, doc)
        else:
            log_info("Machine is reserved by other Job: {}".format(doc["username"]))
            raise Exception("Unable to release the node. Release node manually")


def cleanup_for_blocked_nodes(job_name=None):
    """
    Go through QE-mobile-pool bucket and release unused block nodes
    :return: void
    """
    if job_name is not None:
        query_str = "select meta().id from `{}` where state=\"booked\" and username=\"{}\"".format(BUCKET_NAME, job_name)
    else:
        query_str = "select meta().id from `{}` where state=\"booked\"".format(BUCKET_NAME)
    query = cluster.query(query_str)
    release_node_list = []
    for row in sdk_client.n1ql_query(query):
        doc_id = row["id"]
        result = sdk_client.get(doc_id, quiet=True)
        if not result:
            log_info("Can't access the data for node {}".format(doc_id))
        doc = result.content
        if doc["state"] == "available":
            continue
        job_id = doc["username"]
        if job_id == "":
            job_id = "test_job:123"
        length_array = []
        length_array = job_id.split(":")
        job_name = length_array[0]
        build_id = length_array[1]
        log_info("Releasing node {} for job {}".format(doc_id, job_id))
        if job_name is not None or not is_jenkins_job_running(job_name, build_id):
            doc["prevUser"] = doc["username"]
            doc["username"] = ""
            doc["state"] = "available"
            sdk_client.replace(doc_id, doc)
            release_node_list.append(doc_id)
        else:
            log_info("Job is running, can't release assigned node.")
    if release_node_list:
        log_info("Nodes released back to QE-mobile-pool: {}".format(release_node_list))
    else:
        log_info("No booked node available to be released")


def is_jenkins_job_running(job_name='Net-windows-TestSever-Funtional-tests', build_id=1037):
    jenkins_base_url = "http://uberjenkins.sc.couchbase.com:8080/job/"
    jenkins_url = "{}/{}/{}/api/json".format(jenkins_base_url, job_name, build_id)
    session = Session()
    try:
        resp = None
        resp = session.get(jenkins_url)
        resp.raise_for_status()
        response_code = resp.status_code
        if response_code == 200:
            job_status = resp.json()["result"]
            if job_status is None:
                return True
            return False
        raise Exception("Can't access the job config. Got response code: {}".format(response_code))
    except Exception as err:
        if resp.status_code == 404:
            log_info("Jenkins job is not available - {}".format(jenkins_url))
        else:
            log_info("Exception occurred: {}".format(err))
        return False


if __name__ == "__main__":
    usage = """usage: mobile_server_pool.py
       --num-of-nodes
       --nodes-os-type
       usage: python mobile_server_pool.py
       --num-of-nodes=3 --nodes-os-type=centos
       """

    parser = OptionParser(usage=usage)

    parser.add_option("--num-of-nodes",
                      action="store", dest="num_of_nodes", default=2,
                      help="Specify the no. of node one need from server pool. Default value is 2")

    parser.add_option("--nodes-os-type",
                      action="store", dest="nodes_os_type", default="centos",
                      help="specify the os type of requested node")

    parser.add_option("--nodes-os-version",
                      action="store", dest="nodes_os_version", default="7",
                      help="specify the os version of requested node")

    parser.add_option("--job-name",
                      action="store", dest="job_name",
                      help="specify the job name which is requesting/releasing nodes")

    parser.add_option("--reserve-nodes",
                      action="store_true", dest="reserve_nodes", default=False,
                      help="Use this parameter to request to reserve nodes")

    parser.add_option("--get-available-nodes",
                      action="store_true", dest="get_available_nodes", default=False,
                      help="Use this parameter to get available nodes")

    parser.add_option("--release-nodes",
                      action="store_true", dest="release_nodes", default=False,
                      help="Use this parameter to request to release nodes")

    parser.add_option("--cleanup-nodes",
                      action="store_true", dest="cleanup_nodes", default=False,
                      help="Use this parameter to request to cleanup reserved nodes")

    parser.add_option("--pool-list",
                      action="store", dest="pool_list",
                      help="Pass the list of ips to be release back to QE-mobile-pool.")

    parser.add_option("--sgw-nodes",
                      action="store", dest="sgw_nodes", default=None,
                      help="Pass the list of sgw ips to label on pool.json.")

    parser.add_option("--loadbalancer-nodes",
                      action="store", dest="load_balancer_nodes", default=None,
                      help="Pass the list of load balancer ips to  label on pool.json")
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    if opts.cleanup_nodes and opts.reserve_nodes and opts.release_nodes and opts.get_available_nodes:
        raise Exception("Use either one the flag from --cleanup_nodes or --release-nodes or --reserve-nodes or --get-available-nodes")

    elif opts.get_available_nodes:
        get_nodes_available_from_mobile_pool(opts.nodes_os_type, opts.nodes_os_version)

    elif opts.reserve_nodes:
        log_info("Reserving {} node/s from QE-mobile-pool".format(opts.num_of_nodes))
        node_list = get_nodes_from_pool_server(opts.num_of_nodes, opts.nodes_os_type, opts.nodes_os_version,
                                               opts.job_name)
        log_info("Nodes reserved: {}".format(node_list))
        with open("resources/pool.json", "w") as fh:
            pool_json_str = '{ "ips": ['
            for node in node_list:
                pool_json_str += '"{}", '.format(node)
            if opts.sgw_nodes:
                sgw_node_list = opts.sgw_nodes.strip().split(',')
                for node in sgw_node_list:
                    pool_json_str += '"{}", '.format(node)
            if opts.load_balancer_nodes:
                lp_node_list = opts.load_balancer_nodes.strip().split(',')
                for node in lp_node_list:
                    pool_json_str += '"{}", '.format(node)
            pool_json_str = pool_json_str.rstrip(', ')
            pool_json_str += "],"
            if opts.sgw_nodes:
                pool_json_str += '"ip_to_node_type": {'
                for node in node_list:
                    pool_json_str += '"{}": "couchbase_servers", '.format(node)

                for sgw_node in sgw_node_list:
                    pool_json_str += '"{}": "sync_gateways", '.format(sgw_node)
                if opts.load_balancer_nodes:
                    for lp_node in lp_node_list:
                        pool_json_str += '"{}": "load_balancers", '.format(lp_node)
                pool_json_str = pool_json_str.rstrip(', ')
                pool_json_str += "},"
            pool_json_str = pool_json_str.rstrip(', ')
            pool_json_str += "}"
            fh.write(pool_json_str)
    elif opts.release_nodes:
        try:
            node_list = opts.pool_list.strip().split(',')
        except AttributeError:
            raise AttributeError("Do provide pool node list to release IPs")
        log_info("Releasing nodes {} back to QE-mobile-pool".format(node_list))
        release_node(node_list, opts.job_name)
    elif opts.cleanup_nodes:
        cleanup_for_blocked_nodes(opts.job_name)
    else:
        raise Exception("Use either one the flag from --cleanup_nodes or --release-nodes or --reserve-nodes or --get-available-nodes ")
