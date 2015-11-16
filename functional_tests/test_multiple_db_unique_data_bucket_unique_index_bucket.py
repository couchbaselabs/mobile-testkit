from lib.admin import Admin
from fixtures import cluster

#TODO: Take index or data bucket down and make sure sg goes offline

def test_multiple_db_unique_data_bucket_unique_index_bucket(cluster):

    cluster.reset(config="multiple_dbs_unique_data_unique_index.json")

    # TODO - parametrize
    num_db_users = 5
    num_db2_users = 5
    num_docs_per_user = 100

    admin = Admin(cluster.sync_gateways[0])

    admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="bulk_db_user", number=num_db_users, password="password", channels=["ABC"])
    admin.register_bulk_users(target=cluster.sync_gateways[0], db="db2", name_prefix="bulk_db2_user", number=num_db2_users, password="password", channels=["ABC"])

    users = admin.get_users()

    assert len(users) == 10

    # Round robin
    num_sgs = len(cluster.sync_gateways)
    count = 1
    for user in users.values():
        user.add_docs(num_docs_per_user, uuid_names=True, bulk=True)
        user.target = cluster.sync_gateways[(count + 1) % num_sgs]
        count += 1

    # Build expected ids
    db_ids = []
    db2_ids = []
    for user in users:
        if user.startswith("bulk_db_"):
            u = users[user]
            db_ids.extend(u.cache.keys())
        if user.startswith("bulk_db2_"):
            u = users[user]
            db2_ids.extend(u.cache.keys())

    for user in users:
        if user.startswith("bulk_db_"):
            u = users[user]
            u.verify_ids_from_changes(500, db_ids)
        if user.startswith("bulk_db2_"):
            u = users[user]
            u.verify_ids_from_changes(500, db2_ids)
