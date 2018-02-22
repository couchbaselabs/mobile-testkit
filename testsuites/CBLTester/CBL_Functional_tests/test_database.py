"""import pytest

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query
from CBLClient.DatabaseConfiguration import DatabaseConfiguration


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.database
def test_databaseEncryption(params_from_base_test_setup):
    '''
        @summary:
    '''

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    db = Database(base_url)
    db_configure = DatabaseConfiguration(base_url)
    cbl_db_name = "cbl_db111"
    db_config = db.configure(password="db_password")
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    print "cbl doc ids are {}", cbl_doc_ids
    db.close(cbl_db)
    db_configure.setEncryptionKey(db_config, password="db_password")
    cbl_db1 = db.create(cbl_db_name, db_config)
    cbl_doc_ids = db.getDocIds(cbl_db1)
    print "cbl doc ids are {}", cbl_doc_ids
"""
