import pytest

from time import sleep

from CBLClient.Database import Database
from CBLClient.Replicator_new import Replicator
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.SessionAuthenticator import SessionAuthenticator

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster

class TestReplication(object):
    #base_url = "http://192.168.0.107:8080"
    base_url = "http://172.16.1.154:8080"
    db_obj = Database(base_url)
    cbl_db_name = "cbl_db"
    sg_db = "db"
    replicator_obj = Replicator(base_url)
    repl_config_obj = ReplicatorConfiguration(base_url)
    base_auth_obj = BasicAuthenticator(base_url)
    session_auth_obj = SessionAuthenticator(base_url)
    sg_client = MobileRestClient()

    def test_create(self, params_from_base_test_setup):
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

        sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
        c = cluster.Cluster(config=cluster_config)
        #c.reset(sg_config_path=sg_config)

        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(sourceDb=cbl_db, targetURI=sg_blip_url)
        self.repl_config_obj.setReplicatorType(config, "PUSH_AND_PULL")
        self.repl_config_obj.setContinuous(config, True)
        self.repl_config_obj.setChannels(config, channels)
        authenticator = self.base_auth_obj.create("travel-sample", "password")
        self.repl_config_obj.setAuthenticator(config, authenticator)

        self.db_obj.create_bulk_docs(5, "cbl", db=cbl_db, channels=channels)
        self.sg_client.create_user(sg_admin_url, self.sg_db, "autotest", password="password", channels=channels)
        self.sg_client.create_session(sg_admin_url, self.sg_db, "autotest")

        replicator = self.replicator_obj.create(config)
        self.replicator_obj.toString(replicator)
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

        
