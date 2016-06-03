*** Settings ***

*** Test Cases ***
Stale revision should not be in the index
    [Documentation]
    ...  original ticket: https://github.com/couchbase/couchbase-lite-android/issues/855
    ...  scenario:
    ...  1. Running sync_gateway
    ...  2. Create database and starts both push and pull replicators
    ...  3. Create two or more views
    ...  4. Add doc, and verify doc is index with current revision
    ...  5. Make sure document is pushed to sync gateway
    ...  6. Update doc with sync gateway (not client side)
    ...  7. Make sure updated document is pull replicated to client
    ...  8. Make sure updated document is indexed.
    ...  9. Make sure stale revision is deleted from index.
    ...  10. Pass criteria

*** Keywords ***
