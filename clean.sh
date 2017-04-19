#!/usr/bin/env bash

echo "Cleaning repo"
echo "Removing __pycache__/ ..."
rm -rf __pycache__/

echo "Removing mobile_testkit_tests/__pycache__/ and .cache ..."
rm -rf mobile_testkit_tests/__pycache__/
rm -rf mobile_testkit_tests/.cache/

echo "Removing all .pyc files ..."
find . -name "*.pyc" -exec rm -f {} \;