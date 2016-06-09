*** Settings ***

*** Test Cases ***
Large one-shot push replication could cause out of memory issue (2.5KB/doc * 25,000 docs)
    [Documentation]
    ...  original ticket: https://github.com/couchbase/couchbase-lite-android/issues/898
    ...  scenario:
    ...  1. Running sync_gateway or CouchDB 
    ...  2. Create database and create 25,000 docs (2.5KB/doc) at client by REST API
    ...  3. Start one-shot push replication
    ...  4. Make sure out-of-memory exception should not be thrown.
    ...  5. Pass criteria

*** Keywords ***
