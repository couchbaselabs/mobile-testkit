pipeline {
    agent {label 'sync-gateway-functional-tests-base-cc-centos-7-RUNNER'}
    stages {
        stage('Provision VMs') {
            steps {
                sh '''#!/bin/bash
                export ANSIBLE_CONFIG=libraries/k8s/ansible.cfg
                export ANSIBLE_HOST_KEY_CHECKING=False
                source setup.sh
                source venv/bin/activate
                python utilities/mobile_server_pool.py  --reserve-nodes  --nodes-os-type=centos --num-of-nodes=4
                python libraries/utilities/install_keys.py --public-key-path=~/.ssh/id_rsa.pub --ssh-user=root --ssh-password=couchbase
                python libraries/k8s/generate_inventory.py -i resources/pool.json -o libraries/k8s/inventory.yaml
                ansible -i libraries/k8s/inventory.yaml -m ping all
                '''
            }
        }
        stage('Release VMs') {
            steps {
                sh '''#!/bin/bash
                source venv/bin/activate
                python utilities/mobile_server_pool.py  --release-nodes  --pool-list=$(jq -r '.ips | join(",")' resources/pool.json)
                '''
            }
        }
    }
}