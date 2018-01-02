from time import sleep
import pytest

from CBLClient.Database import Database
from CBLClient.Replicator_new import Replicator
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.SessionAuthenticator import SessionAuthenticator

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster

class TestReplication(object):
    base_url = "http://192.168.0.117:8080"
    #base_url = "http://172.16.1.154:8080"
    db_obj = Database(base_url)
    cbl_db_name = "cbl_db"
    sg_db = "db"
    replicator_obj = Replicator(base_url)
    repl_config_obj = ReplicatorConfiguration(base_url)
    base_auth_obj = BasicAuthenticator(base_url)
    session_auth_obj = SessionAuthenticator(base_url)
    sg_client = MobileRestClient()

    def test_replication_configuration_valid_values(self, params_from_base_test_setup):
        """
        @summary:
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication with valid values of valid cbl Db, valid target url
        3. Start replication with push and pull
        4. Verify replication is successful and verify docs exist
        """

        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_mode = params_from_base_test_setup["mode"]
        cluster_config = params_from_base_test_setup["cluster_config"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels = ["ABC"]

        sg_config = sync_gateway_config_path_for_mode("sync_gateway_blip", sg_mode)
        cluster = Cluster(config=cluster_config)
        cluster.reset(sg_config_path=sg_config)

        cbl_db = self.db_obj.create(self.cbl_db_name)
        self.db_obj.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
        self.sg_client.create_user(sg_admin_url, self.sg_db, "travel-sample", password="password", channels=channels)
        self.sg_client.create_session(sg_admin_url, self.sg_db, "travel-sample")

        authenticator = self.base_auth_obj.create("travel-sample", "password")
        replicator = self.replicator_obj.configure(source_db=cbl_db,
                                                   target_url=sg_blip_url,
                                                   replication_type="PUSH_AND_PULL",
                                                   continuous=True,
                                                   channels=channels,
                                                   replicator_authenticator=authenticator)
        self.replicator_obj.start(replicator)
        sleep(5)
        self.replicator_obj.stop(replicator)
        sg_docs = self.sg_client.get_all_docs(url=sg_admin_url, db=self.sg_db)
        log_info("sg doc full details >><<{}".format(sg_docs["rows"]))

        # Verify database doc counts
        cbl_doc_count = self.db_obj.getCount(cbl_db)
        assert len(sg_docs["rows"]) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

        # Check that all doc ids in SG are also present in CBL
        for doc in sg_docs["rows"]:
            assert self.db_obj.contains(cbl_db, str(doc["id"]))
        self.db_obj.deleteDB(cbl_db)

    @pytest.mark.sanity
    @pytest.mark.listener
    @pytest.mark.parametrize("repl_type, auth_type, sg_docs_count, cbl_docs_count", [
#         ("PUSH", "basic", 10, 5),
#         ("PULL", "basic", 10, 5),
#         ("PUSH", "session", 10, 5),
        ("PULL", "session", 10, 5)
        ])
    def test_replication_configuration_with_one_way_replication(self, params_from_base_test_setup,
                                                                repl_type, auth_type, sg_docs_count, cbl_docs_count):
        sg_url = params_from_base_test_setup["sg_url"]
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_mode = params_from_base_test_setup["mode"]
        cluster_config = params_from_base_test_setup["cluster_config"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels = ["ABC"]
        sg_doc_ids, cbl_db, _ = self.setup_sg_cbl_docs(cluster_config,
                                                       sg_mode, channels,
                                                       sg_blip_url,
                                                       sg_admin_url,
                                                       sg_url,
                                                       cbl_docs_count,
                                                       sg_docs_count,
                                                       auth_type,
                                                       repl_type)
        sg_docs = self.sg_client.get_all_docs(url=sg_admin_url, db=self.sg_db)

        docs_at_cbl = self.db_obj.getCount(cbl_db)
        #cbl_doc_ids = self.db_obj.getDocIds(cbl_db)
        if repl_type == "PUSH":
            sg_final_doc_count = sg_docs_count + cbl_docs_count
            cbl_final_doc_count = cbl_docs_count
        elif repl_type == "PULL":
            sg_final_doc_count = sg_docs_count
            cbl_final_doc_count = cbl_docs_count + sg_docs_count
        assert len(sg_docs["rows"]) == sg_final_doc_count, "Number of sg docs is not equal to total number of cbl docs and sg docs"
        assert docs_at_cbl == cbl_final_doc_count, "Did not get expected number of cbl docs"

        for doc_id in sg_doc_ids:
            # Verify sg docs does not exist in CBL as it is just a push replication
            if repl_type == "PUSH":
                assert not self.db_obj.contains(cbl_db, doc_id)
            # Verify sg docs does exist in CBL as it is a pull replication
            elif repl_type == "PULL":
                assert self.db_obj.contains(cbl_db, doc_id)
        self.db_obj.deleteDB(cbl_db)

    def setup_sg_cbl_docs(self, cluster_config, mode, channels, sg_blip_url,
                          sg_admin_url, sg_url, num_cbl_docs, num_sg_docs,
                          repl_auth_type="basic", repl_type="PULL"):
        # Create CBL database
        cbl_db = self.db_obj.create(self.cbl_db_name)

        # Reset cluster to ensure no data in system
        sg_config = sync_gateway_config_path_for_mode("sync_gateway_blip",
                                                      mode)
        cluster = Cluster(config=cluster_config)
        cluster.reset(sg_config_path=sg_config)

        sg_client = MobileRestClient()
        self.db_obj.create_bulk_docs(num_cbl_docs, "cbl", db=cbl_db,
                                     channels=channels)
        # Add docs in SG
        sg_client.create_user(sg_admin_url, self.sg_db, "travel-sample",
                              password="password", channels=channels)
        cookie, session = sg_client.create_session(sg_admin_url,
                                                   self.sg_db, "travel-sample")
        auth_session = cookie, session
        sg_added_docs = sg_client.add_docs(url=sg_url, db=self.sg_db,
                                           number=num_sg_docs,
                                           id_prefix="sg_doc",
                                           channels=channels,
                                           auth=auth_session)
        sg_added_ids = [row["id"] for row in sg_added_docs]

        # Start and stop continuous replication
        if repl_auth_type == "session":
            replicator_authenticator = self.session_auth_obj.create(session, 60*60, cookie)
        elif repl_auth_type == "basic":
            replicator_authenticator = self.base_auth_obj.create(username="travel-sample", password="password")
        replicator = self.replicator_obj.configure(source_db=cbl_db,
                                                   target_url=sg_blip_url,
                                                   replication_type=repl_type,
                                                   continuous=True,
                                                   channels=channels,
                                                   replicator_authenticator=replicator_authenticator)
        self.replicator_obj.start(replicator)
        sleep(1)
        self.replicator_obj.stop(replicator)

        return sg_added_ids, cbl_db, auth_session
