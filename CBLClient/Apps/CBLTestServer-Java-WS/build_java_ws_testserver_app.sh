#!/bin/bash

EDITION=$1
VERSION=$2
BUILD_NUM=$3

FAIL=0
if [ -z "${ARTIFACTS_DIR}" ] || [ ! -d "${ARTIFACTS_DIR}" ]; then
    echo "Not found: ARTIFACTS_DIR = '$ARTIFACTS_DIR'"
    FAIL=1
fi

if [ -z "${EDITION}" ]; then
    echo 'Undefined: param #1 (edition)'
    FAIL=1
fi

if [ -z "${VERSION}" ]; then
    echo 'Undefined: param #2 (version)'
    FAIL=1
fi

if [ -z "${BUILD_NUM}" ]; then
    echo 'Undefined: param #3 (build-num)'
    FAIL=1
fi

if [ $FAIL -ne 0 ]; then
    echo "Exiting"
    exit $FAIL
fi

export MAVEN_UPLOAD_VERSION=${VERSION}-${BUILD_NUM}
echo "Building version ${MAVEN_UPLOAD_VERSION}"

export PATH=$PATH:$JAVA_HOME

# Build TestServer
echo ./gradlew clean -Dversion=${MAVEN_UPLOAD_VERSION} war
./gradlew clean -Dversion=${MAVEN_UPLOAD_VERSION} war

TESTSERVER_WAR="./build/libs/CBLTestServer-Java-WS-${MAVEN_UPLOAD_VERSION}-${EDITION}.war"
echo $TESTSERVER_WAR
echo ${ARTIFACTS_DIR}/CBLTestServer-Java-WS-${MAVEN_UPLOAD_VERSION}-${EDITION}.war
cp -f ${TESTSERVER_WAR} ${ARTIFACTS_DIR}/CBLTestServer-Java-WS-${MAVEN_UPLOAD_VERSION}-${EDITION}.war

