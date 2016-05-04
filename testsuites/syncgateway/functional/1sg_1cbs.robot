*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_bucket_shadow.py
Library     test_bulk_get_compression.py
Library     test_continuous.py
Library     test_db_online_offline.py
Library     test_db_online_offline_resync.py
Library     test_db_online_offline_webhooks.py
Library     test_longpoll.py
Library     test_multiple_dbs.py
Library     test_multiple_users_multiple_channels_multiple_revisions.py
Library     test_overloaded_channel_cache.py
Library     test_roles.py
Library     test_seq.py
Library     test_single_user_single_channel_doc_updates.py
Library     test_sync.py
Library     test_users_channels.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json
${PROVISION_CLUSTER}        True

*** Test Cases ***
# Cluster has been setup

# test_bulk_get_compression (channel cache mode)
test bulk get compression no compression
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}

test bulk get compression no compression 1.1 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  user_agent=CouchbaseLite/1.1

test bulk get compression accept encoding gzip
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip

test bulk get compression accept encoding gzip 1.1 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip  user_agent=CouchbaseLite/1.1

test bulk get compression x accept part encoding gzip
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  x_accept_part_encoding=gzip

test bulk get compression x accept part encoding gzip 1.1 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  x_accept_part_encoding=gzip  user_agent=CouchbaseLite/1.1

test bulk get compression accept encoding gzip x accept part encoding gzip
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip  x_accept_part_encoding=gzip

test bulk get compression accept encoding gzip x accept part encoding gzip 1.1 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip  x_accept_part_encoding=gzip  user_agent=CouchbaseLite/1.1

test bulk get compression no compression 1.2 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  user_agent=CouchbaseLite/1.2

test bulk get compression accept encoding gzip 1.2 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip  user_agent=CouchbaseLite/1.2

test bulk get compression x accept part encoding gzip 1.2 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  x_accept_part_encoding=gzip  user_agent=CouchbaseLite/1.2

test bulk get compression accept encoding gzip x accept part encoding gzip 1.2 user agent
    [Tags]   sanity
    test bulk get compression   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json    ${300}  accept_encoding=gzip  x_accept_part_encoding=gzip  user_agent=CouchbaseLite/1.2


# test_continuous (channel cache mode)
test continuous changes parametrized 1 user 5000 docs 1 revision
    [Tags]   sanity
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json  ${1}  ${5000}  ${1}

test continuous changes parametrized 50 users 5000 docs 1 revision
    [Tags]   nightly
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json  ${50}  ${5000}  ${1}

test continuous changes parametrized 50 users 10 docs 10 revisions
    [Tags]   sanity
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json  ${50}  ${10}  ${10}

test continuous changes parametrized 50 user 50 docs 1000 revisions
    [Tags]   nightly
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json  ${50}  ${50}  ${1000}

test continuous changes sanity
    [Tags]   sanity
    test_continuous_changes_sanity          ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json  ${10}  ${10}


# test_db_online_offline (channel cache mode)
test online default rest
    [Tags]   sanity
    test online default rest                                                                ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json             ${100}

test offline false config_rest
    [Tags]   sanity
    test offline false config_rest                                                          ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_offline_false_cc.json       ${100}

test online to offline check 503
    [Tags]   sanity
    test online to offline check 503                                                        ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json           ${100}

test online to offline changes feed controlled close continuous
    [Tags]   sanity
    test online to offline changes feed controlled close continuous                         ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json   ${5000}

test online to offline continous changes feed controlled close sanity mulitple users
    [Tags]   sanity
    test online to offline continous changes feed controlled close sanity mulitple users    ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${5000}     ${40}

test online to offline changes feed controlled close longpoll sanity
    [Tags]   sanity
    test online to offline changes feed controlled close longpoll sanity                    ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${5000}

test online to offline longpoll changes feed controlled close sanity mulitple users
    [Tags]   sanity
    test online to offline longpoll changes feed controlled close sanity mulitple users     ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${5000}     ${40}

test online to offline changes feed controlled close longpoll
    [Tags]   sanity
    test online to offline changes feed controlled close longpoll                           ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${5000}

test offline true config bring online
    [Tags]   sanity
    test offline true config bring online                                                   ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_offline_true_cc.json    ${100}

test db offline tap loss sanity dcp
    [Tags]   sanity
    test db offline tap loss sanity                                                         ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_dcp_cc.json     ${100}

test db offline tap loss sanity
    [Tags]   sanity
    test db offline tap loss sanity                                                         ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${100}

test db delayed online
    [Tags]   sanity
    test db delayed online                                                                  ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_cc.json     ${100}

test multiple dbs unique buckets lose tap
    [Tags]   sanity
    test multiple dbs unique buckets lose tap                                               ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_cc.json     ${100}


# test_db_online_offline_resync (channel cache mode)
test bucket online offline resync sanity
    [Tags]   sanity
    test bucket online offline resync sanity    ${5}    ${100}  ${10}

test bucket online offline resync with online
    [Tags]   sanity
    test bucket online offline resync with online   ${5}    ${100}  ${5}

test bucket online offline resync with offline
    [Tags]   sanity
    test bucket online offline resync with offline  ${5}    ${100}  ${5}

# test_db_online_offline_webhooks (channel cache mode)
test webhooks
    [Tags]   sanity
    test webhooks                                   ${5}    ${1}    ${1}    ${2}

test db online offline webhooks offline
    [Tags]   sanity
    test db online offline webhooks offline         ${5}    ${1}    ${1}    ${2}

test db online offline_webhooks offline two
    [Tags]   sanity
    test db online offline_webhooks offline two     ${5}    ${1}    ${1}    ${2}

# test_longpoll (channel cache mode)
test longpoll changes parametrized
    [Tags]   sanity
    test longpoll changes parametrized      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${5000}  ${1}

test longpoll changes parametrized
    [Tags]   sanity
    test longpoll changes parametrized      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${50}   ${100}

test longpoll changes sanity
    [Tags]   sanity
    test longpoll changes sanity            ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${10}   ${10}


# test_multiple_dbs (channel cache mode)
test multiple db unique data bucket unique index bucket
    [Tags]   sanity
    test multiple db unique data bucket unique index bucket     ${SYNC_GATEWAY_CONFIGS}/multiple_dbs_unique_data_unique_index_cc.json   ${10}   ${500}

test multiple db single data bucket single index bucket
    [Tags]   sanity
    test multiple db single data bucket single index bucket     ${SYNC_GATEWAY_CONFIGS}/multiple_dbs_shared_data_shared_index_cc.json   ${10}   ${500}


# test_mulitple_users_mulitiple_channels_mulitple_revisions (channel cache mode)
test mulitple users mulitiple channels mulitple revisions
    [Tags]   sanity
    test mulitple users mulitiple channels mulitple revisions   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${10}   ${3}    ${10}   ${10}


# test overloaded channel cache
test overloaded channel cache one
    [Tags]   sanity
    test overloaded channel cache   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_channel_cache_cc.json  ${5000}  *    True   ${50}

test overloaded channel cache two
    [Tags]   sanity
    test overloaded channel cache   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_channel_cache_cc.json  ${1000}  *    True   ${50}

test overloaded channel cache three
    [Tags]   sanity
    test overloaded channel cache   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_channel_cache_cc.json  ${5000}  ABC  False  ${50}

test overloaded channel cache four
    [Tags]   sanity
    test overloaded channel cache   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_channel_cache_cc.json  ${5000}  ABC  True   ${50}


# test_roles (channel cache mode)
test roles sanity
    [Tags]   sanity
    test roles sanity           ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json


# test_seq (channel cache mode)
test seq
    [Tags]   sanity
    test seq        ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${10}   ${500}  ${1}


# test test_single_user_single_channel_doc_updates (channel cache mode)
test single user single channel doc updates
    [Tags]   sanity
    test single user single channel doc updates     ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json   ${100}  ${100}


# test_sync (channel cache mode)
test issue 1524
    [Tags]   sanity
    test issue 1524            ${SYNC_GATEWAY_CONFIGS}/custom_sync/grant_access_one_cc.json   ${10}

test sync access sanity
    [Tags]   sanity
    test sync access sanity     ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_access_sanity_cc.json

test sync channel sanity
    [Tags]   sanity
    test sync channel sanity    ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_channel_sanity_cc.json

test sync role sanity
    [Tags]   sanity
    test sync role sanity       ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_role_sanity_cc.json

test sync sanity
    [Tags]   sanity
    test sync sanity            ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_one_cc.json

test sync sanity backfill
    [Tags]   sanity
    test sync sanity backfill   ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_one_cc.json

test sync require roles
    [Tags]   sanity
    test sync require roles     ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_require_roles_cc.json


# test_users_channels (channel cache mode)
test multiple users multiple channels
    [Tags]   sanity
    test multiple users multiple channels   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json

test muliple users single channel
    [Tags]   sanity
    test muliple users single channel       ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json

test single user multiple channels
    [Tags]   sanity
    test single user multiple channels      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json

test single user single channel
    [Tags]   sanity
    test single user single channel         ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json


*** Keywords ***
Suite Setup
    Run Keyword If  ${PROVISION_CLUSTER}
    ...  Provision Cluster
    ...     cluster_config=${CLUSTER_CONFIG}
    ...     server_version=${SERVER_VERSION}
    ...     sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...     sync_gateway_config=${SYNC_GATEWAY_CONFIG}

    Verify Cluster Versions
    ...  cluster_config=%{CLUSTER_CONFIG}
    ...  expected_server_version=${SERVER_VERSION}
    ...  expected_sync_gateway_version=${SYNC_GATEWAY_VERSION}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs