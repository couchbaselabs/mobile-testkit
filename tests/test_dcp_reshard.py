import time

from lib.admin import Admin

from cluster_setup import cluster


def test_dcp_reshard(cluster):

    cluster.reset("sync_gateway_default.json")

    start = time.time()

    admin = Admin(cluster.sync_gateways[2])
    admin.register_user(target=cluster.sync_gateways[3], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])
    users = admin.get_users()

    traun = users["traun"]
    seth = users["seth"]

    # Make concurrent and take down a sync_gateway during adds
    print(">>> Adding Traun docs")
    traun.add_docs(8001, uuid_names=True, bulk=True)  # ABC, NBC, CBS

    print(">>> Adding Seth docs")
    seth.add_docs(1999, uuid_names=True)  # FOX

    # verify number of changes
    traun_changes_doc_ids = traun.get_doc_ids_from_changes()
    print("seth number of changes: {}".format(len(traun_changes_doc_ids)))
    assert len(traun_changes_doc_ids) == 8001

    seth_changes_doc_ids = seth.get_doc_ids_from_changes()
    print("traun number of changes: {}".format(len(seth_changes_doc_ids)))
    assert len(seth_changes_doc_ids) == 1999

    total_time = time.time() - start

    print("TIME: {}".format(total_time))
