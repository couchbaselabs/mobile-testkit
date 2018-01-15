from time import sleep
import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster


@pytest.mark.usefixtures("class_init")
class TestReplication(object):
    cbl_db_name = "cbl_db"
    sg_db = "db"

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
        replicator = self.repl_obj.configure(source_db=cbl_db,
                                             target_url=sg_blip_url,
                                             replication_type="PUSH_AND_PULL",
                                             continuous=True,
                                             channels=channels,
                                             replicator_authenticator=authenticator)
        self.repl_obj.start(replicator)
        sleep(5)
        self.repl_obj.stop(replicator)
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
        ("PUSH", "basic", 10, 5),
        ("PULL", "basic", 10, 5),
        ("PUSH", "session", 10, 5),
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
        sg_doc_ids, cbl_db, _, _ = self.setup_sg_cbl_docs(cluster_config,
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
        # cbl_doc_ids = self.db_obj.getDocIds(cbl_db)
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

    @pytest.mark.sanity
    @pytest.mark.listener
    def test_replication_push_replication_without_authentication(self, params_from_base_test_setup):
        """
            @summary:
            1. Create docs in CBL
            2. Create docs in SG
            3. Do push replication without authentication.
            4. Verify docs are not replicated without authentication
        """
        sg_db = "db"
        sg_url = params_from_base_test_setup["sg_url"]
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_mode = params_from_base_test_setup["mode"]
        cluster_config = params_from_base_test_setup["cluster_config"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels = ["ABC"]

        print "set up of conftest is done"

        cbl_db, auth_session = self.setup_sg_cbl_docs(cluster_config,
                                                      sg_mode, channels,
                                                      sg_blip_url,
                                                      sg_admin_url,
                                                      sg_url,
                                                      repl_type="PUSH")[1:3]
        sg_docs = self.sg_client.get_all_docs(url=sg_url, db=sg_db,
                                              auth=auth_session)

        cbl_doc_count = self.db.getCount(cbl_db)
        cbl_doc_ids = self.db.getDocIds(cbl_db)

        assert len(sg_docs["rows"]) == 15, "Number of sg docs is not same previous number before replication as authentication is not provided"

        # Check that all doc ids in CBL are not replicated to SG
        sg_ids = [row["id"] for row in sg_docs["rows"]]
        for doc in cbl_doc_ids:
            assert doc not in sg_ids

    @pytest.mark.sanity
    @pytest.mark.listener
    @pytest.mark.parametrize(
        'replicator_authenticator, invalid_username, invalid_password, invalid_session, invalid_cookie',
        [
            # ('basic', 'invalid_user', 'password', None, None),
            ('session', None, None, 'invalid_session', 'invalid_cookie'),
        ]
    )
    def test_replication_push_replication_invalid_authentication(self, params_from_base_test_setup, replicator_authenticator,
                                                                 invalid_username, invalid_password, invalid_session, invalid_cookie):
        """
            @summary:
            1. Create docs in CBL
            2. Create docs in SG
            3. Do push replication with invalid authentication.
            4. Verify replication configuration fails.

        """
        sg_url = params_from_base_test_setup["sg_url"]
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels = ["ABC"]

        sg_mode = params_from_base_test_setup["mode"]
        cluster_config = params_from_base_test_setup["cluster_config"]
        replicator = self.setup_sg_cbl_docs(cluster_config,
                                            sg_mode, channels,
                                            sg_blip_url,
                                            sg_admin_url,
                                            sg_url,
                                            repl_auth_type=replicator_authenticator,
                                            repl_type="PUSH",
                                            sg_config="listener_tests/listener_tests")[3]
        print self.repl_obj.getStatus()
        """

        sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)

        cbl_doc_count = self.db.getCount(cbl_db)
        cbl_doc_ids = self.db.getDocIds(cbl_db)

        assert len(sg_docs["rows"]) == 10, "Number of sg docs is not same as number of docs before replication"
        assert cbl_doc_count == 5, "Did not get expected number of cbl docs"

        # Check that all doc ids in SG are also present in CBL
        sg_ids = [row["id"] for row in sg_docs["rows"]]
        for doc in cbl_doc_ids:
            assert doc not in sg_ids
        """

    @pytest.mark.sanity
    @pytest.mark.listener
    def test_replication_configuration_with_filtered_doc_ids(self, params_from_base_test_setup):
        """
            @summary:
            1. Create docs in SG
            2. Create docs in CBL
            3. Send doc ids which you want to have replication to the docs ids passed in replication configuration
            4. Verify CBL docs with doc ids sent in configuration got replicated to SG

        """
        sg_db = "db"
        cbl_db_name = "cbl_db"

        sg_url = params_from_base_test_setup["sg_url"]
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        channels = ["ABC"]

        sg_mode = params_from_base_test_setup["sg_mode"]
        cluster_config = params_from_base_test_setup["cluster_config"]

        sg_added_ids, cbl_db, auth_session, replicator = self.setup_sg_cbl_docs(cluster_config,
                                                                                sg_mode, channels,
                                                                                sg_blip_url,
                                                                                sg_admin_url,
                                                                                sg_url,
                                                                                repl_type="PUSH",
                                                                                sg_config="listener_tests/listener_tests")

        # Verify database doc counts
        cbl_doc_count = self.db.getCount(cbl_db)
        cbl_doc_ids = self.db.getDocIds(cbl_db)

        sg_docs = self.sg_client.get_all_docs(url=sg_blip_url, db=sg_db)
        assert len(sg_docs["rows"]) == 15, "Number of sg docs is not equal to total number of cbl docs and sg docs"
        assert cbl_doc_count == 5, "Did not get expected number of cbl docs"

        # Check that all doc ids in SG are also present in CBL
        sg_ids = [row["id"] for row in sg_docs["rows"]]
        for doc in cbl_doc_ids:
            assert doc in sg_ids

        # Verify sg docs does not exist in CBL as it is just a push replication
        # for id in sg_added_doc_ids:
        #    assert id not in cbl_doc_ids

    def test_replication_configuration_with_headers(self, params_from_base_test_setup):
        """
            @summary:
            1. Create docs in CBL
            2. Make replication configuration by authenticating through headers
            4. Verify CBL docs with doc ids sent in configuration got replicated to SG
        """
        sg_db = "db"
        cbl_db_name = "cbl_db"
        num_of_docs = 10

        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_url = params_from_base_test_setup["sg_url"]
        sg_blip_url = params_from_base_test_setup["target_url"]
        channels = ["ABC"]

        # Create CBL database
        cbl_db = self.db.create(cbl_db_name)
        sg_client = MobileRestClient()

        self.db.create_bulk_docs(num_of_docs, "cbll", db=cbl_db, channels=channels)
        cbl_added_doc_ids = self.db.getDocIds(cbl_db)

        # Add docs in SG
        sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
        cookie, session = sg_client.create_session(sg_admin_url, sg_db, "autotest")
        auth_session = cookie, session
        sync_cookie = "{}={}".format(cookie, session)

        session_header = {"Cookie": sync_cookie}

        # repl = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=True, headers=session_header)
        repl = self.repl_obj.configure(cbl_db, target_url=sg_blip_url, continuous=True)

        self.repl_obj.start(repl)
        sleep(1)
        self.repl_obj.stop(repl)
        repl_status_msg = self.repl_obj.getStatus(repl)
        repl_change_listener = self.repl_obj.add_change_listener(repl)
        self.repl_obj.get_changes_changelistener(repl, repl_change_listener)
        print " replicator status msg ", repl_status_msg
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=auth_session)

        # Verify database doc counts
        cbl_doc_ids = self.db.getDocIds(cbl_db)

        assert len(sg_docs["rows"]) == num_of_docs, "Number of sg docs should be equal to cbl docs"
        assert len(cbl_doc_ids) == num_of_docs, "Did not get expected number of cbl docs"

        # Check that all doc ids in CBL are replicated to SG
        sg_ids = [row["id"] for row in sg_docs["rows"]]
        for doc in cbl_doc_ids:
            assert doc in sg_ids

    def setup_sg_cbl_docs(self, cluster_config, mode, channels, sg_blip_url,
                          sg_admin_url, sg_url, num_cbl_docs=5, num_sg_docs=10,
                          repl_auth_type=None, repl_type="PULL", sg_config="sync_gateway_blip"):
        # Create CBL database
        cbl_db = self.db_obj.create(self.cbl_db_name)

        # Reset cluster to ensure no data in system
        sg_config = sync_gateway_config_path_for_mode(sg_config,
                                                      mode)
        cluster = Cluster(config=cluster_config)
        cluster.reset(sg_config_path=sg_config)

        self.db_obj.create_bulk_docs(num_cbl_docs, "cbl", db=cbl_db,
                                     channels=channels)
        # Add docs in SG
        self.sg_client.create_user(sg_admin_url, self.sg_db, "travel-sample",
                                   password="password", channels=channels)
        cookie, session = self.sg_client.create_session(sg_admin_url,
                                                        self.sg_db,
                                                        "travel-sample")
        auth_session = cookie, session
        sg_added_docs = self.sg_client.add_docs(url=sg_url, db=self.sg_db,
                                                number=num_sg_docs,
                                                id_prefix="sg_doc",
                                                channels=channels,
                                                auth=auth_session)
        sg_added_ids = [row["id"] for row in sg_added_docs]

        # Start and stop continuous replication
        if repl_auth_type == "session":
            replicator_authenticator = self.session_auth_obj.create(session, 60 * 60, cookie)
        elif repl_auth_type == "basic":
            replicator_authenticator = self.base_auth_obj.create(username="travel-sample", password="password")
        else:
            replicator_authenticator = None
        replicator = self.repl_obj.configure(source_db=cbl_db,
                                             target_url=sg_blip_url,
                                             replication_type=repl_type,
                                             continuous=True,
                                             channels=channels,
                                             replicator_authenticator=replicator_authenticator)
        self.repl_obj.start(replicator)
        sleep(5)
        self.repl_obj.stop(replicator)

        return sg_added_ids, cbl_db, auth_session, replicator
