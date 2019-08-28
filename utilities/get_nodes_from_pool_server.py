import sys
from optparse import OptionParser
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from keywords.utils import log_info
from couchbase.exceptions import KeyExistsError


SERVER_IP = "172.23.105.177"
USERNAME = 'Administrator'
PASSWORD = 'esabhcuoc'
BUCKET_NAME = "QE-mobile-pool" 


def get_nodes_from_pool_server(num_of_nodes, nodes_os_type, node_os_version, job_name_requesting_node):

    sdk_client = Bucket("couchbase://{}/{}".format(SERVER_IP, BUCKET_NAME))
    log_info("Creating primary index for {}".format(BUCKET_NAME))
    n1ql_query = 'create primary index on {}'.format(BUCKET_NAME)
    query = N1QLQuery(n1ql_query)
    sdk_client.n1ql_query(query)

    # Getting list of available nodes through n1ql query
    query_str = "select meta().id from `{}` where os='{}' " \
                "AND os_version='{}' AND state='available'". format(BUCKET_NAME, nodes_os_type, node_os_version)
    query = N1QLQuery(query_str)
    pool_list = []
    for row in sdk_client.n1ql_query(query):
        doc_id = row["id"]
        node = reserve_node(sdk_client, doc_id, job_name_requesting_node)
        if node:
            pool_list.append(doc_id)
        else:
            continue
        if len(pool_list) == num_of_nodes:
            return pool_list

    # Not able to allocate all the requested nodes, hence release the node back to the pool
    release_node(sdk_client, pool_list, job_name_requesting_node)
    raise Exception("Not enough free node available to satisfy the request")


def reserve_node(sdk_client, doc_id, job_name, counter=0):
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
    except KeyExistsError as err:
        result = sdk_client.get(doc_id)
        doc = result.value
        if doc["state"] != "booked" and counter < 5:
            log_info("Attempt to reserve node {} failed due to error {}".format(err))
            log_info("Re-try attempt no. {}".format(counter))
            return reserve_node(sdk_client, doc_id, job_name, counter+1)
        else:
            log_info("Node has been booked by job {}".format(doc["username"]))
            log_info("Checking for other node")
            return False
    except Exception as err:
        log_info("Exception occured: {}".format(err))
        return False


def release_node(sdk_client, pool_list, job_name):
    for node in pool_list:
        result = sdk_client.get(node)
        doc = result.value
        if doc["username"] == job_name:
            doc["prevUser"] = doc["username"]
            doc["username"] = ""
            doc["state"] = "available"
            sdk_client.replace(node, doc)
        else:
            log_info("Machine is reserved by other Job: {}".format(doc["username"]))
            raise Exception("Unable to release the node. Release node manually")



if __name__ == "__main__":
    usage = """usage: get_nodes_from_pool_server.py
       --num-of-nodes
       --nodes-os-type
       usage: python get_nodes_from_pool_server.py
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

    
    parser.add_option("--job-name-requesting-user",
                      action="store", dest="job_name_requesting_user", default="",
                      help="specify the job anme which is requesting for nodes")
    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    node_list = get_nodes_from_pool_server(opts.num_of_nodes, opts.nodes_os_type, opts.nodes_os_version,
                                            opts.job_name_requesting_user)
    log_info("Nodes reserved: {}".format(node_list))
