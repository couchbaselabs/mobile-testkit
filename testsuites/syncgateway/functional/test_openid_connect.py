from testkit.cluster import Cluster
import requests
import logging
import time
from urlparse import urlparse
from keywords.utils import log_r
from keywords.utils import log_info
from HTMLParser import HTMLParser
from requests import HTTPError
import jwt
import json


DEFAULT_PROVIDER = "test"


class FormActionHTMLParser(HTMLParser):
    """
    Given some HTML, looks for a <form> element, and extracts the "action" attribute
    and saves it to self.form_action
    """

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            for attr_tuple in attrs:
                if attr_tuple[0] == "action":
                    self.form_action = attr_tuple[1]


def extract_cookie(set_cookie_response):
    """
    Given a header string like:

    SyncGatewaySession=0f429ac978005d887131995ef3b1c0459311beff; Path=/db; Expires=Tue, 31 May 2016 21:28:30 GMT

    convert this into a dictionary like:

    {'SyncGatewaySession': '0f429ac978005d887131995ef3b1c0459311beff'}

    """
    name_value_pairs = set_cookie_response.split(";")
    sg_session_pair = name_value_pairs[0]        # SyncGatewaySession=0f429ac978005d887131995ef3b1c0459311beff
    cookie_name = sg_session_pair.split("=")[0]  # SyncGatewaySession
    cookie_val = sg_session_pair.split("=")[1]   # 0f429ac978005d887131995ef3b1c0459311beff
    cookies = {cookie_name: cookie_val}          # {'SyncGatewaySession': '0f429ac978005d887131995ef3b1c0459311beff'}
    return cookies


def discover_authenticate_url(sg_url, sg_db, provider):

    """
    Discover the full url to the authenticate endpoint:

    http://<host>:port/db/_oidc_testing/authenticate?client_id=sync_gateway&redirect_uri=http%3A%2F%2F192.168.0.112%3A4984%2Fdb%2F_oidc_callback&response_type=code&scope=openid+email&state=

    """

    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, provider)

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    return url


def discover_authenticate_endpoint(sg_url, sg_db, provider):
    """
    Discover the authenticate endpoint and parameters.

    The result should look something like this:

    authenticate?client_id=sync_gateway&redirect_uri=http%3A%2F%2F192.168.0.112%3A4984%2Fdb%2F_oidc_callback&response_type=code&scope=openid+email&state=
    """

    # make a request to the _oidc_challenge endpoint
    oidc_challenge_url = "{}/{}/_oidc_challenge?provider={}".format(sg_url, sg_db, provider)
    log_info("Invoking _oidc_challenge against: {}".format(oidc_challenge_url))
    response = requests.get(oidc_challenge_url)

    # the Www-Authenticate header will look something like this:
    # 'OIDC login="http://localhost:4984/db/_oidc_testing/authorize?client_id=sync_gateway&redirect_uri=http%3A%2F%2Flocalhost%3A4984%2Fdb%2F_oidc_callback&response_type=code&scope=openid+email&state="'
    www_auth_header = response.headers['Www-Authenticate']
    max_split = 1
    oidc_login_url = www_auth_header.split("=", max_split)[1]              # '"http://localhost:4984/db/_oid ..."'
    if oidc_login_url.startswith('"') and oidc_login_url.endswith('"'):
        oidc_login_url = oidc_login_url[1:-1]                              # 'http://localhost:4984/db/_oid ...'

    # get the sg hostname, since we need to substitute this for any instances of localhost
    # needed until https://github.com/couchbase/sync_gateway/issues/1849 is fixed
    sg_url_parsed = urlparse(sg_url)
    sg_hostname = sg_url_parsed.hostname
    oidc_login_url = oidc_login_url.replace("localhost", sg_hostname)      # http://192.168.0.112:4984/db/_oid

    # Fetch the oidc_login_url
    response = requests.get(oidc_login_url)
    response.raise_for_status()
    parser = FormActionHTMLParser()
    parser.feed(response.text)
    return parser.form_action


def test_openidconnect_basic_test(sg_url, sg_db, is_admin_port):

    # make a request against the db and expect a 401 response since we haven't authenticated yet.
    # (but there's no point in doing this on the admin port since we'll never get a 401)
    if not is_admin_port:
        db_url = "{}/{}".format(sg_url, sg_db)
        resp = requests.get(db_url)
        assert resp.status_code == 401, "Expected 401 response"

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, DEFAULT_PROVIDER)

    # build the full url
    authenticate_endpoint_url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user')
    }
    authenticate_response = requests.post(authenticate_endpoint_url, files=formdata)
    set_cookie_response_header = authenticate_response.headers['Set-Cookie']
    log_r(authenticate_response)

    # extract the token from the response
    authenticate_response_json = authenticate_response.json()
    id_token = authenticate_response_json["id_token"]
    refresh_token = authenticate_response_json["refresh_token"]

    # make sure the id token has the email field in it
    decoded_id_token = jwt.decode(id_token, verify=False)
    assert "email" in decoded_id_token.keys()

    # make a request using the ID token against the db and expect a 200 response
    headers = {"Authorization": "Bearer {}".format(id_token)}
    db_url = "{}/{}".format(sg_url, sg_db)
    resp = requests.get(db_url, headers=headers)
    log_r(resp)
    assert resp.status_code == 200, "Expected 200 response"

    # make a request using the cookie against the db and expect a 200 response
    db_url = "{}/{}".format(sg_url, sg_db)
    resp = requests.get(db_url, cookies=extract_cookie(set_cookie_response_header))
    log_r(resp)
    assert resp.status_code == 200, "Expected 200 response"

    # make a request using the session_id that's sent in the body
    resp = requests.get(db_url, cookies={"SyncGatewaySession": authenticate_response_json["session_id"]})
    assert resp.status_code == 200, "Expected 200 response"

    # try to use the refresh token to get a few new id_tokens
    id_tokens = [ id_token ]
    for i in xrange(3):

        # This pause is required because according to @ajres:
        # The id_token will only be unique if the two calls are more than a second apart.
        # It would be easy to add an atomically incrementing nonce claim to each token to ensure that they are always unique
        time.sleep(2)

        refresh_token_url = "{}/{}/_oidc_refresh?refresh_token={}&provider={}".format(sg_url, sg_db, refresh_token, "test")
        authenticate_response = requests.get(refresh_token_url)
        authenticate_response_json = authenticate_response.json()
        id_token_refresh = authenticate_response_json["id_token"]
        # make sure we get a unique id token each time
        assert id_token_refresh not in id_tokens
        id_tokens.append(id_token_refresh)


def test_openidconnect_notauthenticated(sg_url, sg_db):

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, DEFAULT_PROVIDER)

    # build the full url
    authenticate_endpoint_url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    formdata = {
        'username': ('', 'testuser'),
        'notauthenticated': ('', 'Return an authorization error for this user')
    }
    response = requests.post(authenticate_endpoint_url, files=formdata)
    assert response.status_code == 401


def test_openidconnect_oidc_challenge_invalid_provider_name(sg_url, sg_db):
    """
    If oidc_challenge is called with an invalid provider name, it should not return
    an Www-Authenticate header
    """

    # make a request to the _oidc_challenge endpoint
    oidc_challenge_url = "{}/{}/_oidc_challenge?provider={}".format(sg_url, sg_db, "bogusprovider")
    response = requests.get(oidc_challenge_url)
    log_info("response.headers: {}".format(response.headers))
    assert "Www-Authenticate" not in response.headers
    assert response.status_code == 400


def test_openidconnect_no_session(sg_url, sg_db):

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user')
    }

    authenticate_url = discover_authenticate_url(sg_url, sg_db, "testnosessions")

    # Make the request to _oidc_testing
    response = requests.post(authenticate_url, files=formdata)
    log_r(response)
    assert "Set-Cookie" not in response.headers


def test_openidconnect_expired_token(sg_url, sg_db):

    token_expiry_seconds = 5

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user'),
        'tokenttl': ('', "{}".format(token_expiry_seconds)),
    }

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, DEFAULT_PROVIDER)

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    response = requests.post(url, files=formdata)
    log_r(response)

    # extract the token from the response
    response_json = response.json()
    id_token = response_json["id_token"]

    time.sleep(token_expiry_seconds * 2)

    # make a request using the ID token against the db and expect a 200 response
    headers = {"Authorization": "Bearer {}".format(id_token)}
    db_url = "{}/{}".format(sg_url, sg_db)
    resp = requests.get(db_url, headers=headers)
    log_r(resp)
    assert resp.status_code != 200, "Expected non-200 response"


def test_openidconnect_garbage_token(sg_url, sg_db):

    token_expiry_seconds = 5

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user'),
        'tokenttl': ('', "{}".format(token_expiry_seconds)),
    }

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, DEFAULT_PROVIDER)

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    response = requests.post(url, files=formdata)
    log_r(response)

    # extract the token from the response
    response_json = response.json()
    id_token = response_json["id_token"]

    # Complete garbage Token
    # make a request using the ID token against the db and expect a 200 response
    headers = {"Authorization": "Bearer {}".format("garbage")}
    db_url = "{}/{}".format(sg_url, sg_db)
    resp = requests.get(db_url, headers=headers)
    log_r(resp)
    assert resp.status_code != 200, "Expected non-200 response"

    # Partial garbage Token

    # get all the components split by "."
    token_components = id_token.split(".")

    # get subset of components except for last one
    all_components_except_last = token_components[:-1]

    # add a garbage last component
    all_components_except_last.append("garbage")

    # create a string out of the components
    partial_garbage_token = ".".join(all_components_except_last)

    headers = {"Authorization": "Bearer {}".format(partial_garbage_token)}
    db_url = "{}/{}".format(sg_url, sg_db)
    resp = requests.get(db_url, headers=headers)
    log_r(resp)
    assert resp.status_code != 200, "Expected non-200 response"


def test_openidconnect_invalid_scope(sg_url, sg_db):

    try:
        discover_authenticate_endpoint(sg_url, sg_db, "testinvalidscope")
    except HTTPError:
        log_info("got expected HTTPError trying to get the authenticate endpoint")
        # ok we got an exception, which is expected since we are using an invalid scope
        return

    raise Exception("Expected HTTPError since we are using invalid scope")


def test_openidconnect_small_scope(sg_url, sg_db):

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user')
    }

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, "testsmallscope")

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    response = requests.post(url, files=formdata)
    log_r(response)

    # extract the token from the response
    response_json = response.json()
    id_token = response_json["id_token"]

    # {u'iss': u'http://localhost:4984/db/_oidc_testing', u'iat': 1466050188, u'aud': u'sync_gateway', u'exp': 1466053788, u'sub': u'testuser'}
    decoded_id_token = jwt.decode(id_token, verify=False)

    assert "email" not in decoded_id_token.keys()


def test_openidconnect_large_scope(sg_url, sg_db):

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user')
    }

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, "testlargescope")

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    response = requests.post(url, files=formdata)
    log_r(response)

    # extract the token from the response
    response_json = response.json()
    id_token = response_json["id_token"]

    # {u'iss': u'http://localhost:4984/db/_oidc_testing', u'iat': 1466050188, u'aud': u'sync_gateway', u'exp': 1466053788, u'sub': u'testuser'}
    decoded_id_token = jwt.decode(id_token, verify=False)

    log_info("decoded_id_token: {}".format(decoded_id_token))

    assert "nickname"  in decoded_id_token.keys()


def test_openidconnect_public_session_endpoint(sg_url, sg_db):

    # multipart/form data content
    formdata = {
        'username': ('', 'testuser'),
        'authenticated': ('', 'Return a valid authorization code for this user')
    }

    # get the authenticate endpoint and query params, should look something like:
    #     authenticate?client_id=sync_gateway&redirect_uri= ...
    authenticate_endpoint = discover_authenticate_endpoint(sg_url, sg_db, DEFAULT_PROVIDER)

    # build the full url
    url = "{}/{}/_oidc_testing/{}".format(
        sg_url,
        sg_db,
        authenticate_endpoint
    )

    # Make the request to _oidc_testing
    response = requests.post(url, files=formdata)
    log_r(response)

    # extract the token from the response
    response_json = response.json()
    id_token = response_json["id_token"]

    headers = {
        "Authorization": "Bearer {}".format(id_token),
        "Content-Type": "application/json"
    }
    url = "{}/{}/_session".format(
        sg_url,
        sg_db
    )

    response = requests.post(url, headers=headers)
    assert "Set-Cookie" in response.headers.keys()
    set_cookie_response = response.headers['Set-Cookie']
    assert "SyncGatewaySession" in set_cookie_response




