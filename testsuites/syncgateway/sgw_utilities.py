from keywords.utils import host_for_url, log_info
from couchbase.bucket import Bucket
from keywords import document


def create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, num_docs):
    cbs_host = host_for_url(cbs_url)
    log_info("Adding docs via SDK...")
    if cbs_cluster.ipv6:
        sdk_client = Bucket('couchbase://{}/{}?ipv6=allow'.format(cbs_host, bucket_name), password='password')
    else:
        sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')
    sdk_client.timeout = 600

    sdk_doc_bodies = document.create_docs('doc_set_two', num_docs)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    log_info("Adding docs done on CBS")
    return sdk_docs, sdk_client
