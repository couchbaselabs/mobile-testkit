*** Settings ***

*** Test Cases ***
Continuous Changes Feed
    [Documentation]
    ...  Testing revolving around the continuous changes feed remaining intact 
    ...  while other operations are occuring on the REST API
    ...
    ...  1. Setup one listener
    ...  2. Create a database
    ...  3. Get _changes?feed=continuous&heartbeat=10000 (or something)
    ...  4. If the above connection closes at any time, the test fails
    ...  5. Add a design document with a map function via the REST API
    ...  6. Add 5000 revisions (total, so about 1 or 2 revs each) of around 3000 documents
    ...  7. Make sure that you received 5000 change events without the connection being closed

*** Keywords ***
