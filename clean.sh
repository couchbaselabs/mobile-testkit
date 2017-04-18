#!/usr/bin/env bash

echo "Cleaning repo"
echo "Removing __pycache__/ ..."
rm -rf __pycache__/

echo "Removing all .pyc files ..."
find . -name "*.pyc" -exec rm -f {} \;