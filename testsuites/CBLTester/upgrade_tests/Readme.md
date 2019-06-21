### CBL Upgrade Summary

1. Migrate older-pre-built db to a provided cbl app
2. Start the replication and replicate db to cluster
3. Running few query tests
    a. Run Query test for Any operator
    b. Run Query test for Between operator
    c. Run FTS Query test
    d. Run Join Query test 
4. Perform mutation operations
    a. Add new docs and replicate to cluster
    b. Update docs for migrated db and replicate to cluster
    c. Delete docs from migrated db and replicate to cluster

### Note
1. One can't run upgrade test for Encrypted CBL DB version lower than 2.1.0 (We are using 2.1.5 as base version for 2.1.0 CBL DB)
2. One can run update for both encrypted and unencrypted db for CBL version 2.1.5 onwards
 