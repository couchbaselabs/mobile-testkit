*** Settings ***
Documentation    Common Variables / Keywords

*** Variables ***
${LIBRARIES}                libraries

${RESOURCES}                resources
${ARTIFACTS}                ${RESOURCES}/artifacts
${SYNC_GATEWAY_CONFIGS}     ${RESOURCES}/sync_gateway_configs
${CLUSTER_CONFIGS}          ${RESOURCES}/cluster_configs

# Suite paths
${SYNC_GATEWAY_SUITE_FUNCTIONAL}  testsuites/syncgateway/functional

*** Keywords ***
Provision Cluster
    [Arguments]     ${server_version}   ${sync_gateway_version}    ${sync_gateway_config}
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${server_arg}               Catenate  SEPARATOR=  --server-version=            ${server_version}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --sync-gateway-version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --sync-gateway-config-file=  ${sync_gateway_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py  ${server_arg}  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

Install Server
    [Arguments]     ${server_version}
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${server_arg}               Catenate  SEPARATOR=  --version=          ${server_version}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_couchbase_server.py  ${server_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

Install Sync Gateway
    [Arguments]     ${sync_gateway_version}  ${sync_gateway_config}
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --config-file=  ${sync_gateway_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_sync_gateway.py  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}


