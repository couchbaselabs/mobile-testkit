import pytest

from lib.admin import Admin
from fixtures import cluster

#TODO: Take index or data bucket down and make sure sg goes offline

@pytest.mark.distributed_index
def test_multiple_db_unique_data_bucket_unique_index_bucket(cluster):

    cluster.reset(config="multiple_dbs_unique_data_unique_index.json")

    # TODO - parametrize
    num_db_users = 5
    num_db2_users = 5
    num_docs_per_user = 100

    admin = Admin(cluster.sync_gateways[0])

    db_one_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="bulk_db_user", number=num_db_users, password="password", channels=["ABC"])
    db_two_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db2", name_prefix="bulk_db2_user", number=num_db2_users, password="password", channels=["ABC"])

    all_users = list(db_one_users)
    all_users.extend(db_two_users)
    assert len(all_users) == 10

    # Round robin
    num_sgs = len(cluster.sync_gateways)
    count = 1
    for user in all_users:
        user.add_docs(num_docs_per_user, uuid_names=True, bulk=True)
        user.target = cluster.sync_gateways[(count + 1) % num_sgs]
        count += 1

    # Build expected ids
    db_one_ids = [key for user in db_one_users for key in user.cache.keys()]
    db_two_ids = [key for user in db_two_users for key in user.cache.keys()]

    # Verify docs for db_one_users
    for user in db_one_users:
        user.verify_ids_from_changes(500, db_one_ids)

    # Verify docs for db_two_users
    for user in db_two_users:
        user.verify_ids_from_changes(500, db_two_ids)
