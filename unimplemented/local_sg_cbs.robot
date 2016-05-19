*** Settings ***
Documentation     A test suite containing functional tests for Sync Gateway
...               revpos handling.
Resource          resources/common.robot

Library           DebugLibrary
Library           ${KEYWORDS}/Document.py
Library           ${KEYWORDS}/MobileRestClient.py
Library           ${KEYWORDS}/SyncGateway.py
...                 version_build=${SYNC_GATEWAY_VERSION}
Library           ${KEYWORDS}/CouchbaseServer.py

Suite Setup       Setup Suite
Test Setup        Setup Test
Test Teardown     Teardown Test

#Suite Teardown    Teardown Suite

Test Timeout      10 minutes     The default test timeout elapsed before the test completed.

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/local_cb.json


*** Test Cases ***
Test Attachment Revpos When Ancestor Unavailable, Active Revision doesn't share ancestor
    Documentation    Creates a document with an attachment, then updates that document so that
    ...              the body of the revision that originally pushed the document is no
    ...              longer available.  Add a new revision that's not a child of the
    ...              active revision, and validate that it's uploaded successfully.
    ...              Example:
    ...                 1. Document is created with no attachment at rev-1
    ...                 2. Server adds revision with attachment at rev-2 {"hello.txt", revpos=2}
    ...                 2. Document is updated multiple times on the server, goes to rev-4
    ...                 3. Client attempts to add a new (conflicting) revision 3a, with ancestors rev-2a (with it's own attachment), rev-1.
    ...                 4. When client attempts to push rev-3a with attachment stub {"hello.txt", revpos=2}.  Should throw an error, since the revpos
    ...                 of the attachment is later than the common ancestor (rev-1)

Test Attachments on Docs Rejected By Sync Function
    Documentation
    ...  1. Start sync_gateway with sync function that rejects all writes:
    ...  function(doc, oldDoc) {
    ...    throw({forbidden:"No writes!"});
    ...  }
    ...  2. Create a doc with attachment
    ...  3. Use CBS sdk to see if attachment doc exists.  Doc ID will look like _sync:att:sha1-Kq5sNclPz7QV2+lfQIuc6R7oRu0= (where the suffix is the digest)
    ...  4. Assert att doc does not exist



*** Keywords ***
Setup Suite
    Download Sync Gateway
    ${cbs_url} =  Install Couchbase Server  host=${COUCHBASE_SERVER_HOST}  version=${COUCHBASE_SERVER_VERSION}
    Set Suite Variable  ${cbs_url}

Setup Test
    Delete Buckets  url=${cbs_url}

Teardown Test
    Shutdown Sync Gateway
#Teardown Suite


Create Doc With Attachment
    Documentation   Adds a document with a test attachment
    ...             Sample doc JSON:
    ...             {"_attachments": {"hello.txt": {"data":"aGVsbG8gd29ybGQ="}}}
    [Arguments]      ${DB_URL} ${DOC_ID}
    [Return]         ${REV_ID}
    ${BODY} =       {"_attachments": {"hello.txt": {"data":"aGVsbG8gd29ybGQ="}}}
    ${response} =    Put Doc ${DB_URL} ${DOC_ID} ${BODY}
    Status Equals    ${response}    201
    ${REV_ID} =      Extract from Response


Update Doc With Attachment Stub
    Documentation    Updates a doc that has an attachment, uses stub to maintain attachment on doc.
    ...              Sample doc JSON:
    ...              {"_rev": "2-02e26ab1d1868f9a3f64285ec50e23a2","_attachments": {"hello.txt": {"stub":true, "revpos":1}}}
    [Arguments]      ${DB_URL} ${DOC_ID} ${REV_ID}
    [Return]         ${NEW_REV_ID}
    ${BODY} =        {"_rev": "${REV_ID}","_attachments": {"hello.txt": {"stub":true, "revpos":1}}}
    ${request} =     Put Doc ${DB_URL} ${DOC_ID} ${BODY}


Update Doc With Conflicting Attachment Stub
    Documentation    Updates a doc that has an attachment, uses stub to maintain attachment on doc.
    ...              Sample doc JSON:
    ...                    {"_rev":"2-foo",
    ...                     "_attachments":{"hello.txt":{"stub":true,"revpos":1}},
    ...                     "_revisions":{
    ...                        "ids":[
    ...                           "foo",
    ...                           "${rev1_id_digest}"
    ...                        ],
    ...                        "start":2
    ...                     }
    ...                    }
    [Arguments]      ${DB_URL} ${DOC_ID} ${PARENT_REV_ID} ${NEW_REV_GEN} ${NEW_REV_HASH} ${EXPECTED_STATUS}
    [Return]         ${NEW_REV_ID}
    ${BODY} =        {"_rev": "${NEW_REV_GEN}-${NEW_REV_HASH}",
    ...                     "_attachments":{
    ...                        "hello.txt":{
    ...                           "stub":true,
    ...                           "revpos":1
    ...                        }
    ...                     },
    ...                     "_revisions":{
    ...                        "ids":[
    ...                           "${NEW_REV_HASH}",
    ...                           "${PARENT_REV_ID}"
    ...                        ],
    ...                        "start":${NEW_REV_GEN}
    ...                     }
    ...                    }
    ${response} = Put Doc ${DB_URL} ${DOC_ID} ${BODY} new_edits==false
    Status Equals    ${response} ${EXPECTED_STATUS}

Put Doc
    Documentation   Basic PUT of a document
    [Arguments]      ${DB_URL} ${DOC_ID} ${BODY}
    [Return]         ${RESPONSE}
    ${request}       HTTP PUT ${DBURL}/${DOC_ID} < ${BODY}
    ${RESPONSE} =    Put ${request}
    Status Equals    ${request}    201


