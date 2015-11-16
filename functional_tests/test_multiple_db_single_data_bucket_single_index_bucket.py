import pytest

from lib.admin import Admin

from fixtures import cluster

@pytest.mark.sanity
def test_multiple_db_single_data_bucket_single_index_bucket(cluster):

    cluster.reset(config="multiple_dbs_shared_data_shared_index.json")

    # TODO - parametrize
    num_db_users = 5
    num_db2_users = 5
    num_docs_per_user = 100

    admin = Admin(cluster.sync_gateways[0])

    admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="bulk_db_user", number=num_db_users, password="password", channels=["ABC"])
    admin.register_bulk_users(target=cluster.sync_gateways[0], db="db2", name_prefix="bulk_db2_user", number=num_db2_users, password="password", channels=["ABC"])

    users = admin.get_users().values()

    assert len(users) == 10

    # Round robin
    num_sgs = len(cluster.sync_gateways)
    count = 1
    for user in users:
        user.add_docs(num_docs_per_user, uuid_names=True, bulk=True)
        user.target = cluster.sync_gateways[(count + 1) % num_sgs]
        count += 1

    all_cache_ids = [key for user in users for key in user.cache.keys()]

    for user in users:
        user.verify_ids_from_changes(1000, all_cache_ids)

