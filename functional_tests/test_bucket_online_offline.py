import pytest
from lib.admin import Admin

from requests.exceptions import HTTPError

from fixtures import cluster

def rest_scan(sync_gateway, db, online=True):

    # Missing ADMIN
    # TODO: GET /{db}/_session/{session-id}
    # TODO: POST /{db}/_session
    # TODO: DELETE /{db}/_session/{session-id}
    # TODO: DELETE /{db}/_user/{name}/_session/{session-id}
    # TODO: DELETE /{db}/_user/{name}/_session

    # TODO: DELETE /{db}/_user/{name}

    # TODO: GET /{db}/_role/
    # TODO: GET /{db}/_role/{name}
    # TODO: POST /{db}/_role/
    # TODO: DELETE /{db}/_role/{name}

    # Missing REST
    # TODO: GET /
    # TODO: POST /{db}/_all_docs
    # TODO: POST /{db}/_bulk_get

    # TODO: POST /{db}
    # TODO: DELETE /{db}/{doc}
    # TODO: PUT /{db}/{doc}/{attachment}
    # TODO: GET /{db}/{doc}/{attachment}

    # Missing Local Document
    # TODO: PUT /{db}/{local-doc-id}
    # TODO: GET /{db}/{local-doc-id}
    # TODO: DELETE /{db}/{local-doc-id}

    # Missing Authentication
    # TODO: POST /{db}/_facebook_token
    # TODO: POST /{db}/_persona_assertion

    admin = Admin(sync_gateway=sync_gateway)

    # PUT /{db}/_role/{name}
    admin.create_role(db=db, name="radio_stations", channels=["HWOD, KDWB"])

    # PUT /{db}/_user/{name}
    seth = admin.register_user(
        target=sync_gateway,
        db=db,
        name="seth",
        password="password", channels=["ABC, CBS"], roles=["radio_stations"])

    # TODO
    # GET /{db}/_user
    users = admin.get_users(db="db")

    # GET /{db}/_user/{name}
    user_info = admin.get_user_info(db="db", name=seth)

    # TODO
    # GET /{db}
    db_info = seth.get_db_info()

    try:
        # PUT /{db}/{name}
        doc = seth.add_doc(doc_id="test-doc-1")

        # GET /{db}/{name}
        # PUT /{db}/{name}
        updated = seth.update_doc(doc_id="test-doc-1", num_revision=1)
    except HTTPError as e:
        print "add_doc exception: {}".format(e)

    try:
        # POST /{db}/_bulk_docs
        docs = seth.add_bulk_docs(doc_ids=["test-doc-2", "test-doc-3"])
    except HTTPError as e:
        print "add_bulk_docs exception: {}".format(e)

    try:
        # GET /{db}/_all_docs
        docs = seth.get_all_docs()
    except HTTPError as e:
        print "get_all_docs exception: {}".format(e)

    try:
        # GET /{db}/_changes
        changes = seth.get_changes()
    except HTTPError as e:
        print "get_all_docs exception: {}".format(e)



@pytest.mark.sanity
def test_online_online_default(cluster):
    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")

    rest_scan(cluster.sync_gateways[0], db="db", online=True)
    rest_scan(cluster.sync_gateways[0], db="offline_db", online=False)

@pytest.mark.sanity
def test_offline_false_config_rest(cluster):
    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false.json")

@pytest.mark.sanity
def test_online__rest(cluster):
    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")







