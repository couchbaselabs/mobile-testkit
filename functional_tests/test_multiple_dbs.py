import pytest

from lib.admin import Admin
from lib.verify import verify_changes

import time

from fixtures import cluster

#TODO: Take index or data bucket down and make sure sg goes offline

@pytest.mark.distributed_index
@pytest.mark.sanity
@pytest.mark.parametrize(
        "conf,num_users,num_docs", [
            ("multiple_dbs_unique_data_unique_index.json", 10, 5000)
        ],
        ids=["DI-1"]
)
def test_multiple_db_unique_data_bucket_unique_index_bucket(cluster, conf, num_users, num_docs):

    # 2 dbs have unique data and unique index buckets
    cluster.reset(config=conf)

    # TODO - parametrize
    num_db_users = num_users
    num_db2_users = num_users
    num_docs_per_user = num_docs

    admin = Admin(cluster.sync_gateways[0])

    db_one_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="bulk_db_user", number=num_db_users, password="password", channels=["ABC"])
    db_two_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db2", name_prefix="bulk_db2_user", number=num_db2_users, password="password", channels=["ABC"])

    all_users = list(db_one_users)
    all_users.extend(db_two_users)
    assert len(all_users) == num_db_users + num_db2_users

    # Round robin
    num_sgs = len(cluster.sync_gateways)
    count = 1
    for user in all_users:
        user.add_docs(num_docs_per_user, bulk=True)
        user.target = cluster.sync_gateways[(count + 1) % num_sgs]
        count += 1

    time.sleep(10)

    # Build expected docs
    db_cache_docs = {k: v for user in db_one_users for k, v in user.cache.items()}
    db2_cache_docs = {k: v for user in db_two_users for k, v in user.cache.items()}

    verify_changes(db_one_users, expected_num_docs=num_docs_per_user * num_db_users, expected_num_revisions=0, expected_docs=db_cache_docs)
    verify_changes(db_two_users, expected_num_docs=num_docs_per_user * num_db2_users, expected_num_revisions=0, expected_docs=db2_cache_docs)

# Kind of an edge case in that most users would not point multiple dbs at the same server bucket
@pytest.mark.distributed_index
@pytest.mark.sanity
def test_multiple_db_single_data_bucket_single_index_bucket(cluster):

    # 2 dbs share the same data and index bucket
    cluster.reset(config="multiple_dbs_shared_data_shared_index.json")

    # TODO - parametrize
    num_db_users = 5
    num_db2_users = 5
    num_docs_per_user = 100

    admin = Admin(cluster.sync_gateways[0])

    db_one_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="bulk_db_user", number=num_db_users, password="password", channels=["ABC"])
    db_two_users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db2", name_prefix="bulk_db2_user", number=num_db2_users, password="password", channels=["ABC"])

    all_users = list(db_one_users)
    all_users.extend(db_two_users)
    assert len(all_users) == num_db_users + num_db2_users

    # Round robin
    num_sgs = len(cluster.sync_gateways)
    count = 1

    for user in all_users:
        user.add_docs(num_docs_per_user, bulk=True)
        user.target = cluster.sync_gateways[(count + 1) % num_sgs]
        count += 1

    # Get list of all docs from users caches
    cached_docs_from_all_users = {k: v for user in all_users for k, v in user.cache.items()}

    # Verify each user has all of the docs
    verify_changes(all_users, expected_num_docs=1000, expected_num_revisions=0, expected_docs=cached_docs_from_all_users)
