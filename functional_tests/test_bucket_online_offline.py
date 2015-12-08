import pytest
from lib.admin import Admin
from lib.verify import verify_changes

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

    # TODO: POST /{db}/_role/
    # TODO: DELETE /{db}/_role/{name}

    # Missing REST
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

    error_responses = {}

    # PUT /{db}/_role/{name}
    try:
        admin.create_role(db=db, name="radio_stations", channels=["HWOD", "KDWB"])
    except HTTPError as e:
        status_code = e.response.status_code
        print "PUT _role exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # GET /{db}/_role
    try:
        roles = admin.get_roles(db=db)
        print(roles)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _role exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # GET /{db}/_role/{name}
    try:
        role = admin.get_role(db=db, name="radio_stations")
        print(role)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _role exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # PUT /{db}/_user/{name}
    try:
        seth = admin.register_user(target=sync_gateway, db=db, name="seth", password="password", channels=["FOX"])
    except HTTPError as e:
        status_code = e.response.status_code
        print "PUT _user exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # GET /{db}/_user
    try:
        users_info = admin.get_users_info(db=db)
        print(users_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _user exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # GET /{db}/_user/{name}
    try:
        user_info = admin.get_user_info(db=db, name="seth")
        print(user_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET _user/<name> exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    # GET /{db}
    try:
        db_info = admin.get_db_info(db=db)
        print(db_info)
    except HTTPError as e:
        status_code = e.response.status_code
        print "GET / exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    try:
        # PUT /{db}/{name}
        doc = seth.add_doc(doc_id="test-doc-1")

        # GET /{db}/{name}
        # PUT /{db}/{name}
        updated = seth.update_doc(doc_id="test-doc-1", num_revision=1)
    except HTTPError as e:
        status_code = e.response.status_code
        print "add_doc exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    try:
        # POST /{db}/_bulk_docs
        docs = seth.add_bulk_docs(doc_ids=["test-doc-2", "test-doc-3"])

        updated = seth.update_doc(doc_id="test-doc-2", num_revision=1)
        updated = seth.update_doc(doc_id="test-doc-3", num_revision=1)

    except HTTPError as e:
        status_code = e.response.status_code
        print "add_bulk_docs exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    try:
        # GET /{db}/_all_docs
        all_docs_result = seth.get_all_docs()
        print(all_docs_result)
        assert len(all_docs_result["rows"]) == 3
    except HTTPError as e:
        status_code = e.response.status_code
        print "get_all_docs exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    try:
        # GET /{db}/_changes
        changes = seth.get_changes()

        verify_changes(seth, expected_num_docs=3, expected_num_revisions=1, expected_docs=seth.cache)
    except HTTPError as e:
        status_code = e.response.status_code
        print "get_all_docs exception: {}".format(status_code)
        error_responses[e.response.url] = status_code

    return error_responses


@pytest.mark.sanity
@pytest.mark.dbonlineoffline
def test_online_online_default(cluster):
    # Scenario 1
    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")

    # all db endpoints should function as expected
    errors = rest_scan(cluster.sync_gateways[0], db="db", online=True)
    assert(len(errors) == 0)


@pytest.mark.sanity
def test_offline_false_config_rest(cluster):
    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false.json")

@pytest.mark.sanity
def test_online__rest(cluster):
    cluster.reset("bucket_online_offline/bucket_online_offline_default.json")







