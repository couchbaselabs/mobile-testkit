*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_continuous.py
Library     test_db_online_offline.py
Library     test_longpoll.py
Library     test_multiple_dbs.py
Library     test_multiple_users_multiple_channels_multiple_revisions.py
Library     test_roles.py
Library     test_seq.py
Library     test_single_user_single_channel_doc_updates.py
Library     test_sync.py
Library     test_users_channels.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_1ac_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Test Cases ***
# Cluster has been setup

# test_continuous (Distributed Index)
test continuous changes parametrized 1 user 5000 docs 1 revision
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json  ${1}  ${5000}  ${1}

test continuous changes parametrized 50 users 5000 docs 1 revision
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json  ${50}  ${5000}  ${1}

test continuous changes parametrized 50 users 5000 10 docs 10 revisions
    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json  ${50}  ${10}  ${10}

#test continuous changes parametrized 50 user 50 docs 1000 revisions
#    test continuous changes parametrized    ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json  ${50}  ${50}  ${1000}

test continuous changes sanity
    test_continuous_changes_sanity          ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json  ${10}  ${10}


# test_db_online_offline (Distributed Index)
test online default rest
    test online default rest                                                                ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json             ${100}

test offline false config_rest
    test offline false config_rest                                                          ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_offline_false_di.json       ${100}

test online to offline check 503
    test online to offline check 503                                                        ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json           ${100}

#test online to offline changes feed controlled close continuous
#    test online to offline changes feed controlled close continuous                         ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json   ${5000}

test online to offline continous changes feed controlled close sanity mulitple users
    test online to offline continous changes feed controlled close sanity mulitple users    ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${5000}     ${40}

test online to offline changes feed controlled close longpoll sanity
    test online to offline changes feed controlled close longpoll sanity                    ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${5000}

test online to offline longpoll changes feed controlled close sanity mulitple users
    test online to offline longpoll changes feed controlled close sanity mulitple users     ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${5000}     ${40}

# test online to offline changes feed controlled close longpoll
#    test online to offline changes feed controlled close longpoll                           ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${5000}

# test offline true config bring online
#    test offline true config bring online                                                   ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_offline_true_di.json    ${100}

test db offline tap loss sanity
    test db offline tap loss sanity                                                         ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${100}

# test db delayed online
#    test db delayed online                                                                  ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_default_di.json     ${100}

test multiple dbs unique buckets lose tap
    test multiple dbs unique buckets lose tap                                               ${SYNC_GATEWAY_CONFIGS}/bucket_online_offline/bucket_online_offline_multiple_dbs_unique_buckets_di.json     ${100}


# test_longpoll (distributed index mode)
test longpoll changes parametrized
    test longpoll changes parametrized      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${5000}  ${1}

test longpoll changes parametrized
    test longpoll changes parametrized      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${50}   ${100}

test longpoll changes sanity
    test longpoll changes sanity            ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${10}   ${10}


# test_multiple_dbs (distributed index mode)
test multiple db unique data bucket unique index bucket
    test multiple db unique data bucket unique index bucket     ${SYNC_GATEWAY_CONFIGS}/multiple_dbs_unique_data_unique_index_di.json   ${10}   ${500}

test multiple db single data bucket single index bucket
    test multiple db single data bucket single index bucket     ${SYNC_GATEWAY_CONFIGS}/multiple_dbs_shared_data_shared_index_di.json   ${10}   ${500}


# test_mulitple_users_mulitiple_channels_mulitple_revisions (distributed index mode)
test mulitple users mulitiple channels mulitple revisions
    test mulitple users mulitiple channels mulitple revisions   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${10}   ${3}    ${10}   ${10}


# test_roles (distributed index mode)
test roles sanity
    test roles sanity           ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json


# test_seq (distributed index mode)
test seq
    test seq        ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${10}   ${500}  ${1}


# test test_single_user_single_channel_doc_updates (distributed index mode)
test single user single channel doc updates
    test single user single channel doc updates     ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json   ${100}  ${100}


# test_sync (Distributed Index)
test issue 1524
     test issue 1524            ${SYNC_GATEWAY_CONFIGS}/custom_sync/grant_access_one_di.json   ${10}

test sync access sanity
    test sync access sanity     ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_access_sanity_di.json

test sync channel sanity
    test sync channel sanity    ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_channel_sanity_di.json

test sync role sanity
    test sync role sanity       ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_role_sanity_di.json

test sync sanity
    test sync sanity            ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_one_di.json

test sync sanity backfill
    test sync sanity backfill   ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_one_di.json

test sync require roles
    test sync require roles     ${SYNC_GATEWAY_CONFIGS}/custom_sync/sync_gateway_custom_sync_require_roles_di.json

# test_users_channels (Distributed Index)
test multiple users multiple channels (distributed index)
    test multiple users multiple channels   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test muliple users single channel (distributed index)
    test muliple users single channel       ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test single user multiple channels (distributed index)
    test single user multiple channels      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test single user single channel (distributed index)
    test single user single channel         ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Keywords ***
Suite Setup
    Log To Console              Setting up ...
    Set Environment Variable    CLUSTER_CONFIG    ${CLUSTER_CONFIG}
    Log                         Using cluster ${CLUSTER_CONFIG}
    Provision Cluster   ${SERVER_VERSION}   ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    Run Keyword If Test Failed      Fetch And Analyze Logs