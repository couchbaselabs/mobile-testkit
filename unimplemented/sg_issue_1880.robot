*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               REST APIs for Design Documents.
...
...               These tests require JavaScript code to be passed in as arguments.
...               For cases where no code is required, like map-only views, just
...               pass in the ${EMPTY} specifier.
...
...               Note also the the use of the pipe-delimiter is not required,
...               but it is recommended on lines where JavaScript is being passed
...               in as using 4 spaces is less readable.
Resource          resources/common.robot
Resource          ./defines.robot
Library           Listener
Suite Setup       Start Listener     ${HOSTNAME}
Test Setup        Create Database    ${DBNAME}
Suite Teardown    Shutdown Listener
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Test Cases ***
Test Incr Retry on Couchbase Node Failure
    Documentation    Start a loop performing single document creates against a multi-node CBS cluster.
    ...              While that loop is running, bring down the CBS node containing the _sync:seq document.
    ...              Verify that there are no documents successfully created with missing sequence values
    [Tags]           Sanity    SG
    [Timeout]        3 minute

    Documentation    Start doc processing loop - repeat 500x (or until CBS node is stopped and wait complete)
    ...              Note - to see a document's sequence, we need to get that doc via the Couchbase SDK
    ...              An alternative might be possible here - docs without a sequence won't get returned by
    ...              a _changes request, so we could just run _changes at the end of the test and verify all
    ...              docs that are successfully written are there and have non-zero sequence numbers.  It's a bit less definitive, but
    ...              a good workaround until we get SDK calls in place.  Note that it's valid for the Add Doc to
    ...              fail while the CBS node is down with error - the bug we're trying to catch here is when the Add Doc
    ...              succeeds, but the document doesn't get assigned a sequence.
    ${doc_gen_1} =  Add Doc  url=${sg_url}  db=${sg_db}  doc=${doc}  auth=${user1}
    ${doc}       =  Get Doc Via Couchbase SDK
    Verify ${doc}._sync.Sequence exists and is non-zero
    Documentation    End Doc processing loop
    ...
    ...              While doc processing loop is running
    Stop             Couchbase Node 1
    Wait             30 seconds

