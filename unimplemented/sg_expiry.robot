*** Settings ***
Documentation    Test suite for Sync Gateway's expiry feature.
...              Functional details (from commit):
... Expiry support for SG documents
...  When writing a document to Sync Gateway (via PUT doc or bulk_docs), users can set the '_exp' property in the body of the document.  When Sync Gateway writes the document, it will:
...  - Set a Couchbase Server expiry on the document, based on the exp value (see below for format)
...  - Strip the _exp property from the document body (to avoid compatibility issues around the leading underscore when that document is replicated elsewhere)
...  - Set an expiry property - `exp` - in the document's sync metadata, to provide some visibility on the expiry value
...
...  When Sync Gateway reads a document (via document GET, bulk_get), it will recreate the _exp property in the body as an ISO-8601 only if the query string includes show_exp=true .
...
...  Supported formats for the incoming _exp value:
...  - JSON number.  Will be treated as a Couchbase Server expiry value (ttl in second when less than 30 days, unix time when greater)
...  - JSON string (numeric format) - same as JSON number
...  - JSON string (as ISO-8601 date).  Converted to Couchbase server expiry value.
...  - JSON null.  Sets expiry to zero (no expiry)
...
...  Note that subsequent updates to the document will use the expiry value on the update.
...  If no expiry value is set on a new revision of a document that was previously set to expire, the new version of the document will have no expiry set.
...
...
...
...
...  Testing Notes
...    1. Setting the _exp property triggers expiry by setting the Couchbase Server expiry for the document.  However, it does NOT remove the document from the in-memory revision cache,
...    where Sync Gateway stores the 5000 most recently requested documents.  Scheduling removal from the rev cache isn't in scope for 1.3, and shouldn't be a significant issue for real-world
...    scenarios (customers who need to manage bucket contents using expiry will typically not have expired docs in their rev cache due to throughput).  However, it has some testing implications:
...      - Attempts to retrieve a document by doc ID after expiry (e.g. GET /db/doc) won't find the doc, as that operation will always attempt to load the latest copy of the doc from the bucket
...      - Attempts to retrieve a document by doc ID AND rev ID after expiry (e.g. GET /db/doc?rev=1-abc) WILL find the doc, as that operation will first attempt to get the doc from the rev cache
...    For this reason, the expiry tests below should use GET /db/doc (without rev) when testing for expiry
...    2. The absolute time expiry tests require the tests to know the Couchbase Server clock (within a few seconds), and calculate a date in various formats a few seconds beyond that time.  If this
...    presents any problems, we can review to see if there's any alternative.
...    3. The tests all attempt to set an expiry 3 seconds in the future, then wait 5 seconds to attempt retrieval.  You can tune that to whatever you think the tolerance of the test framework can
...    handle, such that:
...      - For non-TTL expiry values, you can tune down the 3 seconds, as long as the date doesn't end up in the past by the time it's written to Couchbase Server
...      - You can tune down the wait for attempted get after expiry (from 2s) as long as you avoid race scenarios where the doc hasn't expired by the time you request it.



*** Test Cases ***
Numeric Expiry as TTL
    [Documentation]
    ...  1. PUT /db/doc1 via SG with property "_exp":3
    ...     PUT /db/doc2 via SG with property "_exp":10
    ...  2. Wait five seconds
    ...  3. Get /db/doc1.  Assert response is 404
    ...     Get /db/doc2.  Assert response is 200


String Expiry as TTL
    [Documentation]
    ...  1. PUT /db/doc1 via SG with property "_exp":"3"
    ...     PUT /db/doc2 via SG with property "_exp":"10"
    ...  2. Wait five seconds
    ...  3. Get /db/doc1.  Assert response is 404
    ...     Get /db/doc2.  Assert response is 200


Numeric Expiry as Unix Date
    [Documentation]
    ...  1. Calculate (server time + 3 seconds) as unix time (i.e. Epoch time, e.g. 1466465122)
    ...  2. PUT /db/doc1 via SG with property "_exp":[unix time]
    ...     PUT /db/doc2 via SG with property "_exp":1767225600  (Jan 1 2026)
    ...  3. Wait five seconds
    ...  4. Get /db/doc1.  Assert response is 404
    ...     Get /db/doc2.  Assert response is 200


String Expiry as Unix Date
    [Documentation]
    ...  1. Calculate (server time + 3 seconds) as unix time (i.e. Epoch time, e.g. 1466465122)
    ...  2. PUT /db/doc1 via SG with property "_exp":"[unix time]"
    ...     PUT /db/doc2 via SG with property "_exp":"1767225600"  (Jan 1 2026) Note: the maximum epoch time supported by CBS is maxUint32, or Sun 07 Feb 2106, in case you want to move it out further than 2026.
    ...  3. Wait five seconds
    ...  4. Get /db/doc1.  Assert response is 404
    ...     Get /db/doc2.  Assert response is 200


String Expiry as ISO-8601 Date
    [Documentation]
    ...  1. Calculate (server time + 3 seconds) as ISO-8601 date (e.g. 2016-01-01T00:00:00.000+00:00)
    ...  2. PUT /db/doc1 via SG with property "_exp":"[date]"
    ...     PUT /db/doc2 via SG with property "_exp":"2026-01-01T00:00:00.000+00:00"
    ...  3. Wait five seconds
    ...  4. Get /db/doc1.  Assert response is 404
    ...     Get /db/doc2.  Assert response is 200

Removing expiry
    [Documentation]
    ...  1. PUT /db/doc1 via SG with property "_exp":3
    ...  2. Update /db/doc1 with a new revision with no expiry value
    ...  3. After 10 updates, update /db/doc1 with a revision with no expiry
    ...  3. Get /db/doc1.  Assert response is 200

Rolling TTL
    [Documentation]
    ...  1. PUT /db/doc1 via SG with property "_exp":3
    ...  2. Once per second for 10 seconds, update /db/doc1 with a new revision (also with "_exp":3)
    ...  3. Update /db/doc1 with a revision with no expiry
    ...  3. Get /db/doc1.  Assert response is 200

Setting expiry in bulk docs
    [Documentation]
    ...  1. PUT /db/_bulk_docs with 10 documents.  Set the "_exp":3 on 5 of these documents
    ...  2. Wait five seconds
    ...  3. POST /db/_bulk_get for the 10 documents.  Validate that only the 5 non-expiring documents are returned

Validating retrieval of expiry value (Optional)

    [Documentation]
    ...  I think these scenarios are well-covered by unit tests, so functional tests are probably not strictly required
    ...  unless the functional tests are trying to cover the full API parameter space.
    ...  1. PUT /db/doc1 via SG with property "_exp":100
    ...  2. GET /db/doc1.  Assert response doesn't include _exp property
    ...  3. GET /db/doc1?show_exp=true.  Assert response includes _exp property, and it's a datetime approximately 100 seconds in the future
    ...  4. POST /db/_bulk_docs with doc1 in the set of requested docs.  Assert response doesn't include _exp property
    ...  5. POST /db/_bulk_docs?show_exp=true with doc1 in the set of requested docs.  Assert response includes _exp property, and it's a datetime approx 100s in the future.










