*** Settings ***

*** Test Cases ***
Stale revision should not be in the index
    [Documentation]
    ...  original ticket: https://github.com/couchbase/couchbase-lite-android/issues/855
    ...  scenario:
    ...  1. Running sync_gateway
    ...  2. Create database and starts both push and pull replicators through client REST API
    ...  3. Create two or more views through client REST API
    ...  4. Add doc, and verify doc is index with current revision through client REST API
    ...  5. Make sure document is pushed to sync gateway through sync gateway REST API
    ...  6. Update doc with sync gateway (not client side) through sync gateway REST API
    ...  7. Make sure updated document is pull replicated to client  through client REST API
    ...  8. Make sure updated document is indexed through client REST API
    ...  9. Make sure stale revision is deleted from index.  through client REST API
    ...  10. Pass criteria

*** Keywords ***
