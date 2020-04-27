#!/bin/bash

set -e
ROOT_CA=ca
INTERMEDIATE=int
NODE=pkey
CHAIN=chain
CLUSTER=${1:-172.23.123.176}
USERNAME=${2:-sdkqecertuser}
SSH_PASSWORD=${3:-couchbase}
CLUSTER_VERSION=${4:-5.5.0-1979}
USE_JSON=false

if [[ $CLUSTER_VERSION =~ ^([0-9]+)\.([0-9]+) ]]
then
    major=${BASH_REMATCH[1]}
    minor=${BASH_REMATCH[2]}
fi

if (($minor>=5)); then
    USE_JSON=true
fi


ADMINCRED=Administrator:password
SSH="sshpass -p $SSH_PASSWORD ssh -o StrictHostKeyChecking=no"
SCP="sshpass -p $SSH_PASSWORD scp -o StrictHostKeyChecking=no"

echo Generate ROOT CA
# Generate ROOT CA
openssl genrsa -out ${ROOT_CA}.key 2048 2>/dev/null
openssl req -new -x509  -days 3650 -sha256 -key ${ROOT_CA}.key -out ${ROOT_CA}.pem \
-subj '/C=US/O=couchbase/CN=My Company Root' 2>/dev/null

echo Generate Intermediate
# Generate intemediate key and sign with ROOT CA
openssl genrsa -out ${INTERMEDIATE}.key 2048 2>/dev/null
openssl req -new -key ${INTERMEDIATE}.key -out ${INTERMEDIATE}.csr -subj '/C=US/O=couchbase/CN=My Company Root' 2>/dev/null
openssl x509 -req -in ${INTERMEDIATE}.csr -CA ${ROOT_CA}.pem -CAkey ${ROOT_CA}.key -CAcreateserial \
-CAserial rootCA.srl -extfile v3_ca.ext -out ${INTERMEDIATE}.pem -days 365 2>/dev/null

# Generate client key and sign with ROOT CA and INTERMEDIATE KEY
echo Generate RSA
openssl genrsa -out ${NODE}.key 2048 2>/dev/null
openssl req -new -key ${NODE}.key -out ${NODE}.csr -subj "/C=US/O=couchbase/CN=${USERNAME}" 2>/dev/null
openssl x509 -req -in ${NODE}.csr -CA ${INTERMEDIATE}.pem -CAkey ${INTERMEDIATE}.key -CAcreateserial \
-CAserial intermediateCA.srl -out ${NODE}.pem -days 365 -extfile openssl-san.cnf -extensions 'v3_req'

# Generate certificate chain file
cat ${NODE}.pem ${INTERMEDIATE}.pem ${ROOT_CA}.pem > ${CHAIN}.pem

INBOX=/opt/couchbase/var/lib/couchbase/inbox/
CHAIN=chain.pem

# loop through nodes
echo Get node IPs
hosts=`curl -su Administrator:password http://${CLUSTER}:8091/pools/nodes|jq '.nodes[].hostname'`
arr_hosts=( $hosts )
echo Loop through nodes
for host in "${arr_hosts[@]}"
do
        if  [[ ${host:1:1} == "[" ]] 
        then 
             ip=`echo $host|sed "s/.*\[//;s/\].*//;"`
             echo "${ip}"
             ip="[${ip}]"
        else
             ip=`echo $host|sed 's/\"\([^:]*\):.*/\1/'`
        fi
	      # Copy private key and chain file to a node:/opt/couchbase/var/lib/couchbase/inbox
	      echo "Setup Certificate for ${ip}"

        if  [[ ${host:1:1} == "[" ]]
        then
            new_ip=`echo $ip|sed "s/.*\[//;s/\].*//;"`
            ${SSH} root@${new_ip} "mkdir ${INBOX}" 2>/dev/null || true
            ${SCP} chain.pem root@${ip}:${INBOX}
            ${SCP} pkey.key root@${ip}:${INBOX}
            ${SSH} root@${new_ip} "chmod 777 ${INBOX}${CHAIN}"
            ${SSH} root@${new_ip} "chmod 777 ${INBOX}${NODE}.key"
	else
	    ${SSH} root@${ip} "mkdir ${INBOX}" 2>/dev/null || true
	    ${SCP} chain.pem root@${ip}:${INBOX}
            ${SCP} pkey.key root@${ip}:${INBOX}
	    ${SSH} root@${ip} "chmod o+rx ${INBOX}${CHAIN}"
	    ${SSH} root@${ip} "chmod o+rx ${INBOX}${NODE}.key"
	fi
	if  [[ ${host:1:1} == "[" ]]
	then
	    ip=`echo $ip|sed "s/.*\[//;s/\].*//;"`
	    ip="[${ip}]"
	fi
	# Upload ROOT CA and activate it
	curl -s -o /dev/null --data-binary "@./${ROOT_CA}.pem" http://${ADMINCRED}@${ip}:8091/controller/uploadClusterCA
	curl -sX POST http://${ADMINCRED}@${ip}:8091/node/controller/reloadCertificate
	# Enable client cert
	if ${USE_JSON} ;then
            POST_DATA='{"state": "enable","prefixes": [{"path": "subject.cn","prefix": "","delimiter": ""}]}'
            curl -s -H "Content-Type: application/json" -X POST -d "${POST_DATA}" http://${ADMINCRED}@${ip}:8091/settings/clientCertAuth
	else
            curl -s -d "state=enable" -d "delimiter=" -d "path=subject.cn" -d "prefix=" http://${ADMINCRED}@${ip}:8091/settings/clientCertAuth
        fi
done

# Create keystore file and import ROOT/INTERMEDIATE/CLIENT cert
KEYSTORE_FILE=keystore.jks
STOREPASS=123456

rm -f ${KEYSTORE_FILE}
keytool -genkey -keyalg RSA -alias selfsigned -keystore ${KEYSTORE_FILE} -storepass ${STOREPASS} -validity 360 -keysize 2048 -noprompt \
-dname "CN=${USERNAME}, OU=None, O=None, L=None, S=None, C=US" \
-keypass ${STOREPASS} -storetype pkcs12

keytool -certreq -alias selfsigned -keyalg RSA -file my.csr -keystore ${KEYSTORE_FILE} -storepass ${STOREPASS} -noprompt -storetype pkcs12
openssl x509 -req -in my.csr -CA ${INTERMEDIATE}.pem -CAkey ${INTERMEDIATE}.key -CAcreateserial -out clientcert.pem -days 365
echo Adding ROOT CA
keytool -import -trustcacerts -file ${ROOT_CA}.pem -alias root -keystore ${KEYSTORE_FILE} -storepass ${STOREPASS} -noprompt -storetype pkcs12
echo Adding Intermediate
keytool -import -trustcacerts -file ${INTERMEDIATE}.pem -alias int -keystore ${KEYSTORE_FILE} -storepass ${STOREPASS} -noprompt -storetype pkcs12
keytool -import -keystore ${KEYSTORE_FILE} -file clientcert.pem -alias selfsigned -storepass ${STOREPASS} -noprompt -storetype pkcs12
