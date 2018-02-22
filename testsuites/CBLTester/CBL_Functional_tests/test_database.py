"""
import pytest

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Dictionary import Dictionary
from CBLClient.Document import Document
from CBLClient.Query import Query


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.database
def test_databaseEncryption(params_from_base_test_setup, num_of_docs, continuous):

        @summary:


    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    db = Database(base_url)
    cbl_db_name = "cbl_db"
    db.configure(password="db_password")
    db.create()
"""
