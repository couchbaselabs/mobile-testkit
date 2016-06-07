*** Settings ***

*** Test Cases ***
Bulk User Creation
    [Documentation]    Simple timing test for bulk user creation.
    ...  1. Create 10K users (with some concurrency - maybe 10 workers creating users)
    ...  2. Validate that the 10K users are created in less than x seconds.  Rough target
    ...  should be less than 2 minutes (based on 100ms/user * 10K users / 10 workers = 100s)
    ...  Notes: This should probably end up in a performance test suite, instead of the functional
    ...         test suite, when we get to the point that we're able to run a performance test
    ...         suite in an automated way on a regular basis.  Until then it would be useful to
    ...         include in the functional tests.

*** Keywords ***
