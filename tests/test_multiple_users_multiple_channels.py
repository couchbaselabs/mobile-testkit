import time
import itertools

from lib.user import User
from lib.admin import Admin

from cluster_setup import cluster

def test_1(cluster):

    cluster.reset()

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["NBC", "CBS"])
    admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])

    users = admin.get_users()

    seth = users["seth"]
    adam = users["adam"]
    traun = users["traun"]

    # TODO use bulk docs
    seth.add_docs(2356, uuid_names=True)  # ABC
    adam.add_docs(8198, uuid_names=True)  # NBC, CBS
    traun.add_docs(2999, uuid_names=True)  # ABC, NBC, CBS

    assert len(seth.cache) == 2356
    assert len(adam.cache) == 8198
    assert len(traun.cache) == 2999

    # discuss appropriate time with team
    time.sleep(5)

    c_seth = seth.get_changes()
    assert len(c_seth["results"]) == 5355

    # verify number of changes
    seth_changes_doc_ids = seth.get_doc_ids_from_changes()
    print("seth number of changes: {}".format(len(seth_changes_doc_ids)))
    assert len(seth_changes_doc_ids) == 5355

    adam_changes_doc_ids = adam.get_doc_ids_from_changes()
    print("adam number of changes: {}".format(len(adam_changes_doc_ids)))
    assert len(adam_changes_doc_ids) == 11197

    traun_changes_doc_ids = traun.get_doc_ids_from_changes()
    print("traun number of changes: {}".format(len(traun_changes_doc_ids)))
    assert len(traun_changes_doc_ids) == 13553

    #verify id of docs
    seth_ids = list(itertools.chain(seth.cache.keys(), traun.cache.keys()))
    adam_ids = list(itertools.chain(adam.cache.keys(), traun.cache.keys()))
    traun_ids = list(itertools.chain(seth.cache.keys(), adam.cache.keys(), traun.cache.keys()))

    assert set(seth_changes_doc_ids) == set(seth_ids)
    assert set(adam_changes_doc_ids) == set(adam_ids)
    assert set(traun_changes_doc_ids) == set(traun_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))



