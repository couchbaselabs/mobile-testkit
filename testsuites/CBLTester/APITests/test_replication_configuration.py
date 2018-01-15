import pytest


@pytest.mark.usefixtures("class_init")
class TestReplicatorConfiguration(object):
    cbl_db_name = "cbl_db"

    def test_create(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db,
                                             target_url=sg_blip_url)
        assert self.cbl_db_name == self.db_obj.getName(self.repl_config_obj.getDatabase(config))

    def test_copy(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        copy_config = self.repl_config_obj.copy(config)
        assert copy_config is not None

    def test_get_set_authenticator(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        assert self.repl_config_obj.getAuthenticator(config) == -1
        auth = self.base_auth_obj.create("username", "password")
        self.repl_config_obj.setAuthenticator(config, auth)
        assert self.repl_config_obj.getAuthenticator(config) is not None

    def test_get_set_channels(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        assert self.repl_config_obj.getChannels(config) == -1
        channels = ["ABC"]
        self.repl_config_obj.setChannels(config, channels)
        assert channels == self.repl_config_obj.getChannels(config)

    def test_get_set_continous(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        assert not self.repl_config_obj.isContinuous(config)
        self.repl_config_obj.setContinuous(config, True)
        assert self.repl_config_obj.isContinuous(config)

    def test_get_set_documentIds(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        assert self.repl_config_obj.getDocumentIDs(config) == -1
        doc_ids = ["testID"]
        self.repl_config_obj.setDocumentIDs(config, doc_ids)
        assert self.repl_config_obj.getDocumentIDs(config) == doc_ids

    def test_get_set_replicatorType(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        replication_types = ["PUSH", "PULL", "PUSH_AND_PULL"]
        for repl_type in replication_types:
            self.repl_config_obj.setReplicatorType(config, repl_type)
            assert repl_type == self.repl_config_obj.getReplicatorType(config)

    def test_get_target(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        assert sg_blip_url == self.repl_config_obj.getTarget(config)

    def test_get_set_pinnnedServerCertificates(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        # assert 0

    def test_get_set_get_set_conflictResolver(self, params_from_base_test_setup):
        sg_admin_url = params_from_base_test_setup["sg_admin_url"]
        sg_blip_url = sg_admin_url.replace("http", "blip")
        sg_blip_url = "{}/db".format(sg_blip_url)
        cbl_db = self.db_obj.create(self.cbl_db_name)
        config = self.repl_config_obj.create(source_db=cbl_db, target_url=sg_blip_url)
        # assert 0
