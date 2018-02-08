#!/bin/bash -ex
# http://mobile.jenkins.couchbase.com/view/Core_Based_Builds/job/

BRANCH=${1}
VERSION=${2}
BLD_NUM=${3}
EDITION=${4}


if [[ ! -d mobile-testkit ]]
then
    git clone https://github.com/couchbaselabs/mobile-testkit.git 
fi

cd mobile-testkit

# Get code updates

git clean -dfx
git checkout ${BRANCH}
git pull
git log -3
git status

git submodule update --init --recursive
cd CBLClient/Apps/CBLTestServer-iOS
if [[ ! -d Frameworks ]]; then mkdir Frameworks; fi

# Prepare framework
SCHEME=CBLTestServer-iOS
SDK=iphonesimulator
SDK_DEVICE=iphoneos
FRAMEWORK_DIR=${WORKSPACE}/CBLClient/Apps/CBLTestServer-iOS/Frameworks/

if [[ -d build ]]; then rm -rf build/*; fi
if [[ -d ${FRAMEWORK_DIR} ]]; then rm -rf ${FRAMEWORK_DIR}/*; fi

pushd ${FRAMEWORK_DIR}
pwd
cp /latestbuilds/couchbase-lite-ios/${VERSION}/ios/${BLD_NUM}/couchbase-lite-ios-${EDITION}_${VERSION}-${BLD_NUM}.zip .
unzip couchbase-lite-swift_${EDITION}_${VERSION}-${BLD_NUM}.zip
cp -r iOS/CouchbaseLiteSwift.framework .
cp -r iOS/CouchbaseLiteSwift.framework.dSYM .
# cp Extras/*.a .
# cp Extras/*.h .
popd

# Build LiteServ

TESTSERVER_APP=${SCHEME}.app
TESTSERVER_APP_DEVICE=${SCHEME}-Device.app
TESTSERVER_ZIP=${SCHEME}.zip
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK} -configuration Release -derivedDataPath build
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK_DEVICE} -configuration Release -derivedDataPath build-device -allowProvisioningUpdates

rm -f *.zip
cp -rf build/Build/Products/Release-${SDK}/${TESTSERVER_APP} .
cp -rf build-device/Build/Products/Release-${SDK_DEVICE}/${TESTSERVER_APP} ./${TESTSERVER_APP_DEVICE}
zip -ry ${TESTSERVER_ZIP} *.app

echo "Done!"
