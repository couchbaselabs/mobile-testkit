#!/usr/bin/env bash

liteserv_branch=$1

if [ "$#" -ne 1 ]; then
    echo "You must provide 'master' or a branch name for LiteServ"
    exit 1
fi

cd deps/couchbase-lite-android-liteserv/

git checkout $liteserv_branch
if [ $? -ne 0 ]; then
    echo "Failed to checkout: $liteserv_branch"
    exit 1
fi

# Build and deploy liteserv android
./gradlew clean && ./gradlew assemble


