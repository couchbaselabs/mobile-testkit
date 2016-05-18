*** Settings ***
Documentation     A test suite containing functional tests for Sync Gateway
...               revpos handling.
Resource          resources/common.robot
Resource          ./defines.robot
Library           Listener
Suite Setup       Start Listener     ${HOSTNAME}
Test Setup        Create Database    ${DBNAME}
Suite Teardown    Shutdown Listener
Test Timeout      10 minutes     The default test timeout elapsed before the test completed.

*** Test Cases ***
Test Attachment Revpos When Ancestor Unavailable
    Documentation    Creates a document with an attachment, then updates that document so that
    ...              the body of the revision that originally pushed the document is no
    ...              longer available.  Add a new revision that's not a child of the
    ...              active revision, and validate that it's uploaded successfully.
    ...              Example:
    ...                 1. Document is created with attachment at rev-1
    ...                 2. Document is updated multiple times on the server, goes to rev-4
    ...                 3. Client attempts to add a new (conflicting) revision 2, with parent rev-1.
    ...                 4. If the body of rev-1 is no longer available on the server (temporary backup of revision has expired, and is no longer stored
    ...                   in the in-memory rev cache), we were throwing an error to client
    ...                   because we couldn't verify based on the _attachments property in rev-1.
    ...                 5. In this scenario, before returning error, we are now checking if the active revision has a common ancestor with the incoming revision.
    ...                  If so, we can validate any revpos values equal to or earlier than the common ancestor against the active revision.



    [Tags]           Sanity    Attachments
    ${dburl} =       http://localhost:4985/default
    ${docid} =       TestDoc

    ${doc1} =       Create Doc With Attachment  url=${sg_url}  db=${db}  doc_id=${docid}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${doc1.id} ${doc1.revid}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}

    Documentation   In order to remove ensure rev 1 isn't available from the in-memory revision cache, restart SG and wait 5 minutes for archived
    ...             version to expire from bucket.  TODO: Add config to reduce the 5 minute expiry time for testing purposes
    Stop Sync Gateway
    Start Sync Gateway
    Wait five minutes for doc to expire from CBS (or even better, delete the backup document directly via the SDK)
    (when it's implemented, could also set the expiry config property https://github.com/couchbase/sync_gateway/issues/1729)

    Documentation   Create a conflicting revision with revision 1 as ancestor, referencing revpos
    ${revid} =      Update Doc With Conflicting Attachment Stub ${dburl} ${docid} ${rev1id} 2 foo 201

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
    ...                           "${rev1_id}"
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


