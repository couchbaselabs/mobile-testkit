#!/bin/bash

EDITION=$1
VERSION=$2
BLD_NUM=$3

export ANDROID_HOME=/home/couchbase/jenkins/tools/android-sdk
export PATH=$PATH:$ANDROID_SDK_HOME/tools:$ANDROID_SDK_HOME/platform-tools
export MAVEN_UPLOAD_VERSION=${VERSION}-${BLD_NUM}

cd ${WORKSPACE}/mobile-testkit/CBLClient/Apps/CBLTestServer-Android

# Build TestServer
echo ./gradlew clean && ./gradlew -Dversion=${MAVEN_UPLOAD_VERSION} assemble
./gradlew clean && ./gradlew -Dversion=${MAVEN_UPLOAD_VERSION} assemble

TESTSERVER_APK=app/build/outputs/apk/debug/app-debug.apk
if [ -e ${TESTSERVER_APK} ]
then
    cp -f ${TESTSERVER_APK} ${WORKSPACE}/artifacts_${EDITION}/CBLTestServer-Android-${MAVEN_UPLOAD_VERSION}-${EDITION}-debug.apk
else
    exit 1
fi
