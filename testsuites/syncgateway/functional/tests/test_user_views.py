import pytest
import json
import time

from keywords import document
from keywords import attachment


from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.views
@pytest.mark.role
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize("sg_conf_name", [
    "user_views/user_views",
])
def test_user_views_sanity(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'single_user_multiple_channels'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_db = "db"
    number_docs_per_channel = 100

    topology = params_from_base_test_setup["cluster_topology"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_public_url = topology["sync_gateways"][0]["public"]

    client = MobileRestClient()

    # Issue GET /_user to exercise principal views
    users = client.get_users(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(users) == 2 and "seth" in users and "raghu" in users

    # Issue GET /_role to exercise principal views
    roles = client.get_roles(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(roles) == 2 and "Scientist" in roles and "Researcher" in roles

    # These are defined in the sg config

    # Scientist role has channels ["Download"]
    # Researcher role has channels ["Upload"]

    # "seth" has "Scientist" role and ["Create"] channel
    # "raghu" has "Researcher" role and ["Edit"] channel

    seth_session = client.create_session(url=sg_admin_url, db=sg_db, name="seth", password="pass")
    raghu_session = client.create_session(url=sg_admin_url, db=sg_db, name="raghu", password="pass")

    start = time.time()

    download_doc_bodies = document.create_docs(
        doc_id_prefix="download_doc",
        number=number_docs_per_channel,
        attachments_generator=attachment.generate_2_png_100_100,
        channels=["Download"]
    )
    upload_doc_bodies = document.create_docs(
        doc_id_prefix="upload_doc",
        number=number_docs_per_channel,
        attachments_generator=attachment.generate_png_100_100,
        channels=["Upload"]
    )
    create_doc_bodies = document.create_docs(
        doc_id_prefix="create_doc",
        number=number_docs_per_channel,
        attachments_generator=attachment.generate_2_png_100_100,
        channels=["Create"]
    )
    edit_doc_bodies = document.create_docs(
        doc_id_prefix="edit_doc",
        number=number_docs_per_channel,
        attachments_generator=attachment.generate_png_100_100,
        channels=["Edit"]
    )

    end = time.time() - start
    log_info("Time to create docs: {}s".format(end))

    download_docs = client.add_bulk_docs(
        url=sg_public_url,
        db=sg_db,
        docs=download_doc_bodies,
        auth=seth_session
    )
    assert len(download_docs) == number_docs_per_channel

    upload_docs = client.add_bulk_docs(
        url=sg_public_url,
        db=sg_db,
        docs=upload_doc_bodies,
        auth=raghu_session
    )
    assert len(upload_docs) == number_docs_per_channel

    create_docs = client.add_bulk_docs(
        url=sg_public_url,
        db=sg_db,
        docs=create_doc_bodies,
        auth=seth_session
    )
    assert len(create_docs) == number_docs_per_channel

    edit_docs = client.add_bulk_docs(
        url=sg_public_url,
        db=sg_db,
        docs=edit_doc_bodies,
        auth=raghu_session
    )
    assert len(edit_docs) == number_docs_per_channel

    design_doc = {
        "views": {
            "filtered": {
                "map": 'function(doc, meta) {emit(doc.name, null);}'
            }
        }
    }

    client.add_design_doc(url=sg_admin_url, db=sg_db, name="test_views", doc=json.dumps(design_doc))

    import pdb
    pdb.set_trace()

    # Need to retry until this returns results, with max retry value
    filtered = client.get_view(url=sg_public_url, db=sg_db, design_doc_name="test_views", view_name="filtered", auth=seth_session)
    log_info(filtered)

    import pdb
    pdb.set_trace()

