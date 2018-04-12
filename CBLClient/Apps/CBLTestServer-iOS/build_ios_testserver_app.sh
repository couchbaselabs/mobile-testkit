#!/bin/bash

EDITION=$1
VERSION=$2
BLD_NUM=$3
cd ${WORKSPACE}/mobile-testkit/CBLClient/Apps/CBLTestServer-iOS
if [[ ! -d Frameworks ]]; then mkdir Frameworks; fi

# Prepare framework
if [ EDITION = "community" ]
then
SCHEME=CBLTestServer-iOS
else
SCHEME=CBLTestServer-iOS-EE
fi
SDK=iphonesimulator
SDK_DEVICE=iphoneos
FRAMEWORK_DIR=${WORKSPACE}/mobile-testkit/CBLClient/Apps/CBLTestServer-iOS/Frameworks

if [[ -d build ]]; then rm -rf build/*; fi
if [[ -d ${FRAMEWORK_DIR} ]]; then rm -rf ${FRAMEWORK_DIR}/*; fi

pushd ${FRAMEWORK_DIR}
pwd
IOS_ZIP=${WORKSPACE}/artifacts/couchbase-lite-swift_${EDITION}_${VERSION}-${BLD_NUM}.zip
if [[ -f ${IOS_ZIP} ]]; then
    unzip ${IOS_ZIP}
    cp -r iOS/CouchbaseLiteSwift.framework .
    cp -r iOS/CouchbaseLiteSwift.framework.dSYM .
else
    echo "Required file ${IOS_ZIP} not found!"
    exit 1
fi
popd

# Build LiteServ

TESTSERVER_APP=CBLTestServer-iOS.app
TESTSERVER_APP_DEVICE=CBLTestServer-iOS-Device.app
TESTSERVER_APP_CP=${SCHEME}-${VERSION}-${BLD_NUM}.app
TESTSERVER_APP_DEVICE_CP=${SCHEME}-${VERSION}-${BLD_NUM}-Device.app
TESTSERVER_DEBUG_APP_CP=${SCHEME}-${VERSION}-${BLD_NUM}-debug.app
TESTSERVER_DEBUG_APP_DEVICE_CP=${SCHEME}-${VERSION}-${BLD_NUM}-Device-debug.app
TESTSERVER_ZIP=CBLTestServer-iOS-${EDITION}-${VERSION}-${BLD_NUM}.zip
if [ EDITION = "community" ]
then
configuration=Release
product_location=Release-${SDK}
device_prod_loc=Release-${SDK_DEVICE}
debug_configuration=Debug
debug_product_location=Debug-${SDK}
debug_device_prod_loc=Debug-${SDK_DEVICE}
else
configuration=Release-EE
product_location=Release-EE-${SDK}
device_prod_loc=Release-EE-${SDK_DEVICE}
debug_configuration=Debug-EE
debug_product_location=Debug-EE-${SDK}
debug_device_prod_loc=Debug-EE-${SDK_DEVICE}
fi
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK} -configuration ${configuration} -derivedDataPath build
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK_DEVICE} -configuration ${configuration} -derivedDataPath build-device -allowProvisioningUpdates
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK} -configuration ${debug_configuration} -derivedDataPath build
xcodebuild CURRENT_PROJECT_VERSION=${BLD_NUM} CBL_VERSION_STRING=${VERSION} -scheme ${SCHEME} -sdk ${SDK_DEVICE} -configuration ${debug_configuration} -derivedDataPath build-device -allowProvisioningUpdates

rm -f *.zip
cp -rf build/Build/Products/${product_location}/${TESTSERVER_APP} ./${TESTSERVER_APP_CP}
cp -rf build-device/Build/Products/${device_prod_loc}/${TESTSERVER_APP} ./${TESTSERVER_APP_DEVICE_CP}
cp -rf build/Build/Products/${debug_product_location}/${TESTSERVER_APP} ./${TESTSERVER_DEBUG_APP_CP}
cp -rf build-device/Build/Products/${debug_device_prod_loc}/${TESTSERVER_APP} ./${TESTSERVER_DEBUG_APP_DEVICE_CP}
zip -ry ${WORKSPACE}/artifacts/${TESTSERVER_ZIP} *.app

echo "Done!"
