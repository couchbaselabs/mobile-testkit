import pytest
import json
import time

from keywords import document
from keywords import attachment
from keywords import couchbaseserver

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from utilities.cluster_config_utils import persist_cluster_config_environment_prop


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.views
@pytest.mark.role
@pytest.mark.channel
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.attachments
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("user_views/user_views", False),
    ("user_views/user_views", True)
])
def test_user_views_sanity(params_from_base_test_setup, sg_conf_name, x509_cert_auth):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'single_user_multiple_channels'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))
    persist_cluster_config_environment_prop(cluster_conf, 'x509_certs', x509_cert_auth)
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_db = "db"
    number_docs_per_channel = 100

    topology = params_from_base_test_setup["cluster_topology"]
    cbs_url = topology["couchbase_servers"][0]
    bucket = "data-bucket"
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_public_url = topology["sync_gateways"][0]["public"]

    client = MobileRestClient()

    # These are defined in the sg config

    # Scientist role has channels ["Download"]
    # Researcher role has channels ["Upload"]

    # "seth" has "Scientist" role and ["Create"] channel
    # "raghu" has "Researcher" role and ["Edit"] channel

    # Issue GET /_user to exercise principal views
    users = client.get_users(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(users) == 2 and "seth" in users and "raghu" in users

    # Issue GET /_role to exercise principal views
    roles = client.get_roles(url=sg_admin_url, db=sg_db)

    # These are defined in the config
    assert len(roles) == 2 and "Scientist" in roles and "Researcher" in roles

    # Verify channels on each role
    scientist_role = client.get_role(url=sg_admin_url, db=sg_db, name="Scientist")
    researcher_role = client.get_role(url=sg_admin_url, db=sg_db, name="Researcher")

    assert len(scientist_role["all_channels"]) == 2
    assert "Download" in scientist_role["all_channels"]
    assert "!" in scientist_role["all_channels"]

    assert scientist_role["name"] == "Scientist"
    assert len(scientist_role["admin_channels"]) == 1 and "Download" in scientist_role["admin_channels"]

    assert len(researcher_role["all_channels"]) == 2
    assert "Upload" in researcher_role["all_channels"]
    assert "!" in researcher_role["all_channels"]

    assert researcher_role["name"] == "Researcher"
    assert len(researcher_role["admin_channels"]) == 1 and "Upload" in researcher_role["admin_channels"]

    # Verify roles are assigned to the user
    seth_user = client.get_user(url=sg_admin_url, db=sg_db, name="seth")
    raghu_user = client.get_user(url=sg_admin_url, db=sg_db, name="raghu")

    assert len(seth_user["all_channels"]) == 3
    assert "!" in seth_user["all_channels"] and "Create" in seth_user["all_channels"] and "Download" in seth_user["all_channels"]
    assert seth_user["admin_roles"] == ["Scientist"]
    assert seth_user["roles"] == ["Scientist"]

    assert len(raghu_user["all_channels"]) == 3
    assert "!" in raghu_user["all_channels"] and "Edit" in raghu_user["all_channels"] and "Upload" in raghu_user["all_channels"]
    assert raghu_user["admin_roles"] == ["Researcher"]
    assert raghu_user["roles"] == ["Researcher"]

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

    # Assert that the attachment docs gets written to couchbase server
    server = couchbaseserver.CouchbaseServer(cbs_url)
    server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att:", ipv6=cluster.ipv6)
    expected_num_attachments = (number_docs_per_channel * 2) + \
        number_docs_per_channel + \
        (number_docs_per_channel * 2) + \
        number_docs_per_channel
    assert len(server_att_docs) == expected_num_attachments

    design_doc = {
        "views": {
            "filtered": {
                "map": 'function(doc, meta) {emit(meta._id, doc.channels);}'
            },
            "filtered_more": {
                "map": 'function(doc, meta) { if (doc.channels.indexOf("Create") != -1 || doc.channels.indexOf("Edit") != -1) {emit(meta._id, doc.channels);}}'
            }
        }
    }

    client.add_design_doc(url=sg_admin_url, db=sg_db, name="test_views", doc=json.dumps(design_doc))

    # "seth" should see docs for channels ["Create", "Download"]
    seth_filtered = client.get_view(
        url=sg_public_url,
        db=sg_db,
        design_doc_name="test_views",
        view_name="filtered",
        auth=seth_session
    )
    seth_filtered_rows = seth_filtered["rows"]
    validate_rows(
        rows=seth_filtered_rows,
        num_expected_rows=2 * number_docs_per_channel,
        expected_id_prefixes=["create_doc", "download_doc"],
        number_of_prefixed_docs=number_docs_per_channel
    )

    # "seth" should only see docs with "Create" channel through this view
    seth_filtered_more = client.get_view(
        url=sg_public_url,
        db=sg_db,
        design_doc_name="test_views",
        view_name="filtered_more",
        auth=seth_session
    )
    seth_filtered_more_rows = seth_filtered_more["rows"]
    validate_rows(
        rows=seth_filtered_more_rows,
        num_expected_rows=number_docs_per_channel,
        expected_id_prefixes=["create_doc"],
        number_of_prefixed_docs=number_docs_per_channel
    )

    # "raghu" should see docs for channels ["Upload", "Edit"]
    raghu_filtered = client.get_view(
        url=sg_public_url,
        db=sg_db,
        design_doc_name="test_views",
        view_name="filtered",
        auth=raghu_session
    )
    raghu_rows = raghu_filtered["rows"]
    validate_rows(
        rows=raghu_rows,
        num_expected_rows=2 * number_docs_per_channel,
        expected_id_prefixes=["upload_doc", "edit_doc"],
        number_of_prefixed_docs=number_docs_per_channel
    )

    # "raghu" should only see docs with "Edit" channel through this view
    raghu_filtered_more = client.get_view(
        url=sg_public_url,
        db=sg_db,
        design_doc_name="test_views",
        view_name="filtered_more",
        auth=raghu_session
    )
    raghu_filtered_more_rows = raghu_filtered_more["rows"]
    validate_rows(
        rows=raghu_filtered_more_rows,
        num_expected_rows=number_docs_per_channel,
        expected_id_prefixes=["edit_doc"],
        number_of_prefixed_docs=number_docs_per_channel
    )


def validate_rows(rows, num_expected_rows, expected_id_prefixes, number_of_prefixed_docs):
    log_info("Validating rows has length: {}".format(num_expected_rows))
    assert len(rows) == num_expected_rows

    log_info("Validating rows has doc_prefixes: {}".format(expected_id_prefixes))
    ids = [row["id"] for row in rows]
    total_expected_doc_ids = []
    for expected_id_prefix in expected_id_prefixes:
        total_expected_doc_ids += ["{}_{}".format(expected_id_prefix, i) for i in range(number_of_prefixed_docs)]

    for expected_id in total_expected_doc_ids:
        assert expected_id in ids
        ids.remove(expected_id)
    assert len(ids) == 0
