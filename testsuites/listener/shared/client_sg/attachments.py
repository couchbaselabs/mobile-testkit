import time
import filecmp

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from keywords.utils import log_info
from keywords.Document import Document
from keywords.utils import breakpoint
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker


def test_inline_large_attachments(ls_url, cluster_config):

    """...  1.  Start LiteServ and Sync Gateway
    ...  2.  Create 2 databases on LiteServ (ls_db1, ls_db2)
    ...  3.  Start continuous push replication from ls_db1 to sg_db
    ...  4.  Start continuous pull replication from sg_db to ls_db2
    ...  5.  PUT 5 large inline attachments to ls_db1
    ...  6.  DELETE the docs on ls_db1
    ...  7.  PUT same 5 large inline attachments to ls_db1
    ...  8.  Verify docs replicate to ls_db2
    ...  9.  Purge ls_db1
    ...  10. Verify docs removed"""

    log_info("Running 'test_inline_large_attachments' ...")

    log_info(cluster_config)

    sg_url = cluster_config["sync_gateways"][0]["admin"]
    sg_url_admin = cluster_config["sync_gateways"][0]["public"]

    log_info("ls_url: {}".format(ls_url))
    log_info("sg_url: {}".format(sg_url))
    log_info("sg_url_admin: {}".format(sg_url_admin))

    ls_db1 = "ls_db1"
    ls_db2 = "ls_db2"
    sg_db = "db"

    client = MobileRestClient()
    client.create_database(ls_url, ls_db1)
    client.create_database(ls_url, ls_db2)

    # Start continuous push replication from ls_db1 -> sg_db
    repl_one = client.start_replication(
        url=ls_url,
        continuous=True,
        from_db=ls_db1,
        to_url=sg_url, to_db=sg_db
    )

    # Start continuous push replication from sg_db -> ls_db2
    repl_two = client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_url, from_db=sg_db,
        to_db=ls_db2
    )

    # doc with 2.36 PNG attachment
    doc_generator = Document()
    attachment_docs = []
    for i in range(5):
        doc = doc_generator.create_doc(
            id="large_attach_{}".format(i),
            attachment_name="golden_gate_large.jpg",
            channels=["ABC"]
        )
        attachment_docs.append(doc)

    # add large attachments to ls_db1
    docs = []
    for doc in attachment_docs:
        docs.append(client.add_doc(ls_url, ls_db1, doc, use_post=False))

