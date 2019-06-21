### CBL Upgrade Summary

1. Migrate older-pre-built db to a provided cbl app
2. Start the replication and replicate db to cluster
3. Running few query tests
    - Run Query test for Any operator
    - Run Query test for Between operator
    - Run FTS Query test
    - Run Join Query test 
4. Perform mutation operations
    - Add new docs and replicate to cluster
    - Update docs for migrated db and replicate to cluster
    - Delete docs from migrated db and replicate to cluster

### Note
1. One can't run upgrade test for Encrypted CBL DB version lower than 2.1.0 (We are using 2.1.5 as base version for 2.1.0 CBL DB)
2. One can run update for both encrypted and unencrypted db for CBL version 2.1.5 onwards
 