#!/usr/bin/env bash

echo "Pulling log.html"
scp root@172.23.105.118:/var/jenkins/workspace/centos7-robot-sync-gateway-functional-tests/mobile-testkit/log.html .
echo "Pulling report.html"
scp root@172.23.105.118:/var/jenkins/workspace/centos7-robot-sync-gateway-functional-tests/mobile-testkit/report.html .
echo "Pulling output.xml"
scp root@172.23.105.118:/var/jenkins/workspace/centos7-robot-sync-gateway-functional-tests/mobile-testkit/output.xml .
