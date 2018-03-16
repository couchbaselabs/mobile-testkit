#!/bin/bash -ex

branch=${1}
VERSION=${2}
BLD_NUM=${3}
EDITION=${4}
FINAL_RELEASE=false
#export GRADLE_USER_HOME=${WORKSPACE} 
#export ANDROID_HOME=/home/couchbase/jenkins/tools/android-sdk
export ANDROID_HOME=~/Library/Android/sdk

if [ "$FINAL_RELEASE" = true ]
then
    export MAVEN_UPLOAD_VERSION=${VERSION}
else
    export MAVEN_UPLOAD_VERSION=${VERSION}-${BLD_NUM}
fi

# Remove /home/couchbase/.m2 local repo since it is not getting updated properly durning Android build and  
# indirectly causing Liteserv build to fail. Ideally, Liteserv needs to change setting to not use local maven
# if [ -d ~/.m2 ] ; then rm -rf /home/couchbase/.m2 ; fi

git clone https://github.com/couchbaselabs/mobile-testkit.git

cd mobile-testkit
git checkout ${branch}
git pull
git log -3
git status

cd CBLClient/Apps/CBLTestServer-Android
# Build TestServer

    echo ./gradlew clean && ./gradlew -Dversion=${MAVEN_UPLOAD_VERSION} assemble
    ./gradlew clean && ./gradlew -Dversion=${MAVEN_UPLOAD_VERSION} assemble

TESTSERVER_APK=app/build/outputs/apk/debug/app-debug.apk
if [ -e ${TESTSERVER_APK} ]
then
    cp -f ${TESTSERVER_APK} CBLTestServer-Android-${MAVEN_UPLOAD_VERSION}-debug.apk
else
    exit 1
fi

LATESTBUILDS_CBLITE=http://latestbuilds.hq.couchbase.com/couchbase-lite-android/${VERSION}/${VERSION}-${BLD_NUM}
echo ........................... upload internally to ${LATESTBUILDS_CBLITE}
