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
    [Tags]           Sanity    Attachments
    ${dburl} =       http://localhost:4985/default
    ${docid} =       TestDoc

    ${rev1id} =       Create Doc With Attachment ${dburl} ${docid}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${rev1id}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}
    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}

    Documentation   In order to remove ensure rev 1 isn't available from the in-memory revision cache, restart SG and wait 5 minutes for archived
    ...             version to expire from bucket.  TODO: Add config to reduce the 5 minute expiry time for testing purposes
    Stop Sync Gateway
    Start Sync Gateway
    Wait 5 minutes

    Documentation   Create a conflicting revision with revision 1 as ancestor, referencing revpos
    ${revid} =      Update Doc With Conflicting Attachment Stub ${dburl} ${docid} ${rev1id} 2 foo 201


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
    ${response} = Put Doc ${DB_URL} ${DOC_ID} ${BODY}
    Status Equals    ${response} ${EXPECTED_STATUS}

Put Doc
    Documentation   Basic PUT of a document
    [Arguments]      ${DB_URL} ${DOC_ID} ${BODY}
    [Return]         ${RESPONSE}
    ${request}       HTTP PUT ${DBURL}/${DOC_ID} < ${BODY}
    ${RESPONSE} =    Put ${request}
    Status Equals    ${request}    201


