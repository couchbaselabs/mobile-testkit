*** Settings ***
Resource          resources/common.robot

Library     ${Libraries}/NetworkUtils.py
Library     ${Libraries}/LoggingKeywords.py
Library     ${Keywords}/CouchbaseServer.py

Test Setup      Setup Test
Test Teardown   Teardown Test

*** Test Cases ***
Test Attachment Revpos When Ancestor Unavailable
    [Documentation]    Creates a document with an attachment, then updates that document so that
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
    [Tags]           sanity    attachments  syncgateway

    Set Test Variable  ${cbs_url}  ${cluster_hosts["couchbase_servers"][0]}
    Set Test Variable  ${sg_url}  ${cluster_hosts["couchbase_servers"][0]}

    ${sg_db_bucket} =  Create Bucket  url=${cbs_url}  name=db-bucket
    ${sg_db} =  Set Variable  testdb

    ${sg_url}  ${sg_url_admin} =  Start Sync Gateway
    ...  config=${SYNC_GATEWAY_CONFIG}
    ...  db=${sg_db}
    ...  host=${SYNC_GATEWAY_HOST}
    ...  port=${SYNC_GATEWAY_PORT}
    ...  admin_port=${SYNC_GATEWAY_ADMIN_PORT}
    ...  server_url=${cbs_url}
    ...  server_bucket=${sg_db_bucket}

    ${channels_list} =  Create List  NBC
    ${user1} =  Create User  url=${sg_url_admin}  db=${sg_db}  name=user_1  password=password  channels=${channels_list}
    ${doc_with_att} =  Create Doc  id=att_doc  content={"sample_key": "sample_val"}  attachment=sample_text.txt  channels=${channels_list}

    ${doc_rev_1} =  Add Doc  url=${sg_url}  db=${sg_db}  doc=${doc_with_att}  auth=${user1}
    ${doc_rev_2} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_rev_1["id"]}  number_updates=${1}  auth=${user1}
    ${doc_rev_4} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_rev_1["id"]}  number_updates=${2}  auth=${user1}

    ${doc_rev_2_conflict} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_rev_1["id"]}  number_updates=${1}  auth=${user1}  rev=${doc_rev_2["rev"]}

    Debug

    #${doc_handle} =  Add Doc  url=${sg_url}  db=${db}  ${doc}

     #Debug

#    ${dburl} =       http://localhost:4985/default
#    ${docid} =       TestDoc
#
#    ${doc1} =       Create Doc With Attachment  url=${sg_url}  db=${db}  doc_id=${docid}
#    ${revid} =       Update Doc With Attachment Stub ${dburl} ${doc1.id} ${doc1.revid}
#    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}
#    ${revid} =       Update Doc With Attachment Stub ${dburl} ${docid} ${revid}

    # In order to remove ensure rev 1 isn't available from the in-memory revision cache, restart SG and wait 5 minutes for archived
    # version to expire from bucket.  TODO: Add config to reduce the 5 minute expiry time for testing purposes

#    Stop Sync Gateway
#    Start Sync Gateway

    # Wait five minutes for doc to expire from CBS (or even better, delete the backup document directly via the SDK)
    # (when it's implemented, could also set the expiry config property https://github.com/couchbase/sync_gateway/issues/1729)

    # Create a conflicting revision with revision 1 as ancestor, referencing revpos

    #${revid} =      Update Doc With Conflicting Attachment Stub ${dburl} ${docid} ${rev1id} 2 foo 201

*** Keywords ***
Setup Test
    Log  Using cluster %{CLUSTER_CONFIG}  console=True
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}
    Delete Buckets  url=${cluster_hosts["couchbase_servers"][0]}

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs

