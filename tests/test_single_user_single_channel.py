import time
from lib.admin import Admin

from cluster_setup import cluster


def test_1(cluster):

    cluster.reset()

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    users = admin.get_users()
    print users

    seth = users["seth"]
    admin = users["admin"]

    seth.add_docs(7000, uuid_names=True)
    admin.add_docs(3000, uuid_names=True)

    assert len(seth.docs_info) == 7000
    assert len(admin.docs_info) == 3000

    seth_changes = seth.get_changes()
    admin_changes = admin.get_changes()

    print("Number of changes(seth): " + str(len(seth_changes["results"])))
    print("Number of changes(admin): " + str(len(admin_changes["results"])))

    assert len(seth_changes["results"]) == 7000
    assert len(admin_changes["results"]) == 10000

    end = time.time()
    print("TIME:{}s".format(end - start))

