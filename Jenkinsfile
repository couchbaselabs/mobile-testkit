pipeline {
    agent {label 'sync-gateway-functional-tests-base-cc-centos-7-RUNNER || sync-gateway-functional-tests-docker'}
    stages {
        stage('Provision VMs') {
            steps {
                sh 'source setup.sh'
                sh 'source venv/bin/activate'
                sh 'python3 --version'
            }
        }
    }
}