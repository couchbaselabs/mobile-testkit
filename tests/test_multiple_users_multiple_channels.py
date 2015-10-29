import time

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

    assert len(seth.docs_info) == 2356
    assert len(adam.docs_info) == 8198
    assert len(traun.docs_info) == 2999

    # discuss appropriate time with team
    time.sleep(5)

    c_seth = seth.get_changes()
    assert len(c_seth["results"]) == 5355

    c_adam = adam.get_changes()
    assert len(c_adam["results"]) == 11197

    # ABC
    c_traun = traun.get_changes()
    assert len(c_traun["results"]) == 13553

    end = time.time()
    print("TIME:{}s".format(end - start))



