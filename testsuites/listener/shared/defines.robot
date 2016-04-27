*** Settings ***
Documentation     Global settings and variables defined for all Listener tests.

*** Variables ***
${DBNAME}           foo
${VIEW1_NAME}       fizz
${VIEW2_NAME}       buzz
${LITESERV_HOSTNAME}         localhost
${LITESERV_PORT}             ${59840}
${SYNC_GATEWAY_HOSTNAME}     localhost
${USERNAME}         demo
${PASSWORD}         pass

*** Keywords ***
