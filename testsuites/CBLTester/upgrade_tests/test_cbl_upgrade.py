import time
import pytest

from CBLClient.Database import Database
from keywords.utils import log_info


@pytest.mark.listener
@pytest.mark.upgrade_test
def test_upgrade_cbl(params_from_base_suite_setup):
    base_liteserv_version = params_from_base_suite_setup["base_liteserv_version"]
    upgraded_liteserv_version = params_from_base_suite_setup["upgraded_liteserv_version"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    upgrade_cbl_db_name = "upgarded" + str(time.time())
    base_url = params_from_base_suite_setup["base_url"]
    upgrade_from_encrypted_db = params_from_base_suite_setup["encrypted_db"]
    db_password = params_from_base_suite_setup["db_password"]

    supported_base_liteserv = ["1.4", "2.0", "2.1.5", "2.5.0"]
    db = Database(base_url)
    if upgrade_from_encrypted_db:
        db_config = db.configure(password=db_password)
        db_prefix = "travel-sample-encrypted"
    else:
        db_config = db.configure()
        db_prefix = "travel-sample"

    if base_liteserv_version in supported_base_liteserv:
        old_liteserv_db_name = db_prefix + "-" + base_liteserv_version
    else:
        pytest.skip("Run test with one of supported base liteserv version - ".format(supported_base_liteserv))

    if liteserv_platform == "android":
        prebuilt_db_path = "/assets/{}.cblite2.zip".format(old_liteserv_db_name)
    elif liteserv_platform == "xamarin-android":
        prebuilt_db_path = "{}.cblite2.zip".format(old_liteserv_db_name)
    else:
        prebuilt_db_path = "Databases/{}.cblite2".format(old_liteserv_db_name)

    log_info("Copying db of CBL-{} to CBL-{}".format(base_liteserv_version, upgraded_liteserv_version))
    db.copyDatabase(prebuilt_db_path, upgrade_cbl_db_name, db_config)
    cbl_db = db.create(upgrade_cbl_db_name, db_config)
    cbl_doc_ids = db.getDocIds(cbl_db, limit=40000)
    assert len(cbl_doc_ids) == 31591

    # Cleaning the database , tearing down
    db.deleteDB(cbl_db) 