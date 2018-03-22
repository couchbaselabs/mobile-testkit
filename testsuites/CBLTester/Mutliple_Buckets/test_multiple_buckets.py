import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from keywords import document

from libraries.testkit import cluster

@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("num_of_docs", [200000])
def test_mutlitple_buckets(params_from_base_suite_setup, num_of_docs):
    """
        @summary:
    """

    sg_url = params_from_base_suite_setup["sg_url"]
    sg_admin_url = params_from_base_suite_setup["sg_admin_url"]
    target_url = params_from_base_suite_setup["target_url"].rsplit('/', 1)[0]
    base_url = params_from_base_suite_setup["base_url"]
    cluster_config = params_from_base_suite_setup["cluster_config"]
    sg_config = params_from_base_suite_setup["sg_config"]
    db_obj = Database(base_url)
    repl_obj = Replication(base_url)

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_dbs = ["db1", "db2", "db3", "db4", "db5", "db6", "db7", "db8", "db9"]
    channels = ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZA"]
    usernames = ["autotest1", "autotest2", "autotest3", "autotest4", "autotest5", "autotest6", "autotest7", "autotest8", "autotest9"]
    db_names = ["cbl_db1", "cbl_db2", "cbl_db3", "cbl_db4", "cbl_db5", "cbl_db6", "cbl_db7", "cbl_db8", "cbl_db9"]
    sg_client = MobileRestClient()

    # populating content on SG/CBS for different buckets
    for username, channel, sg_db in zip(usernames, channels, sg_dbs):
        sg_client.create_user(sg_admin_url, sg_db, username, password="password", channels=[channel])
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
        session = cookie, session_id
        sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                       channels=[channel])
        sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
        assert len(sg_docs) == num_of_docs

    db_lists = []
    try:
        for username, channel, sg_db, db_name in zip(usernames, channels, sg_dbs, db_names):
            print "*" * 60
            print "Starting Replication between SG DB - '{}' and CBL DB - '{}'".format(sg_db, db_name)
            print "*" * 60
            sg_blip_url = target_url + '/' + sg_db
            config = db_obj.configure()
            cbl_db = db_obj.create(db_name, config)
            db_lists.append(cbl_db)
            session, _, replicator = repl_obj.create_session_configure_replicate(
                base_url, sg_admin_url, sg_db, username, "password", [channel], sg_client, cbl_db, sg_blip_url, continuous=False)
            repl_obj.wait_until_replicator_idle(replicator)
            total = repl_obj.getTotal(replicator)
            completed = repl_obj.getCompleted(replicator)
            assert total == completed, "total is not equal to completed"
            time.sleep(5)  # wait until replication is over
            doc_count = db_obj.getCount(cbl_db)
            print "Checking doc count in db {}: {}".format(db_name, doc_count)
            assert num_of_docs == doc_count
    except Exception, err:
        print "Exception occurred - ", str(err)
        assert 1
    finally:
        print "Deleting DBs from CBL:"
        for cbl_db in db_lists:
            db_obj.deleteDB(cbl_db)
    