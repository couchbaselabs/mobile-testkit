pipeline {
    agent {label 'sync-gateway-functional-tests-base-cc-centos-7-RUNNER'}
    stages {
        stage('Provision VMs') {
            steps {
                sh '''#!/bin/bash
                source setup.sh
                source venv/bin/activate
                python utilities/mobile_server_pool.py  --reserve-nodes  --nodes-os-type=centos --num-of-nodes=4
                POOL=$(jq '.ips | join(",")' resources/pool.json)
                echo $POOL
                '''
            }
        }
        stage('Release VMs') {
            steps {
                sh '''#!/bin/bash
                python utilities/mobile_server_pool.py  --release-nodes  --pool-list=$POOL
                unset POOL
                '''
            }
        }
    }
}