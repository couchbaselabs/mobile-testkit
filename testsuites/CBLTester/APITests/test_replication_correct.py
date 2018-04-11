import pytest

from time import sleep

from keywords.MobileRestClient import MobileRestClient
from libraries.testkit import cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords.utils import log_info

from CBLClient.Database import Database
from CBLClient.Replicator_new import Replicator
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.SessionAuthenticator import SessionAuthenticator

#baseUrl = "http://172.16.1.154:8080"
baseUrl = "http://192.168.0.109:8080"
baseUrl2 = "http://10.0.2.17:8080"
class TestReplication(object):
    
    replication_config_obj = ReplicatorConfiguration(baseUrl)
    replicator_obj = Replicator(baseUrl)
    db_obj = Database(baseUrl)
    #db_obj = Database(baseUrl2)
    base_auth_obj = BasicAuthenticator(baseUrl)
    session_auth_obj = SessionAuthenticator(baseUrl)

    @pytest.mark.sanity
    @pytest.mark.listener
    def test_start(self, params_from_base_test_setup):

        sg_db = "db"
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_mode = "cc"
        cluster_config = params_from_base_test_setup["cluster_config"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels_sg = ["ABC"]

        sourceDb = self.db_obj.create("sourceDb")
        sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
        sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
        c = cluster.Cluster(config=cluster_config)
        c.reset(sg_config_path=sg_config)

        sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels_sg)
        session = sg_client.create_session(sg_admin_url, sg_db, "autotest")

        # Create bulk doc json
        bulk_doc = {"repl_0": {"c": "d", "e": "f"},
                    "repl_1": {"g": "h", "i": "j"},
                    "repl_2": {"2": "3", "4": "5"},
                    "repl_3": {"g": "h", "i": "j"}
                    }

        self.db_obj.addDocuments(sourceDb, bulk_doc)
        #targetDb = self.db_obj2.create("targetDb") #this a db on other client
        config = self.replication_config_obj.create(sourceDb, targetURI=sg_blip_url)
        authenticator = self.base_auth_obj.create("couchbase",
                                                  "couchbase")
        self.replication_config_obj.setAuthenticator(config,
                                                     authenticator)
        self.replication_config_obj.setContinuous(config, True)
        self.replication_config_obj.setChannels(config, channels_sg)
        replicator = self.replicator_obj.create(config)
        replicator.start()
        sleep(1)
        self.replicator_obj.stop(replicator)
        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
        log_info("sg doc full details >><<{}".format(sg_docs["rows"]))
    
        # Verify database doc counts
        cbl_doc_count = self.db_obj.getCount(sourceDb)
        cbl_docs = self.db_obj.getDocuments(sourceDb)
        log_info("All cbl docs are {}".format(cbl_docs))
        assert len(sg_docs["rows"]) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
    
        # Check that all doc ids in SG are also present in CBL
        for doc in sg_docs["rows"]:
            assert self.db_obj.contains(sourceDb, str(doc["id"]))