#!/usr/bin/env bash
# This scripts attempts to setup an environment for running mobile testkit tests.
# 1. Check that you have Python 2.7 and virtualenv installed
# 2. Installs venv/ in this directory containing a python 2.7 interpreter
# 3. Installs all pip packages required by this repo
# 4. Adds custom library paths to your PYTHONPATH

# py37version=$(python3.7 -c 'import sys; print("{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))')
py3version=$(python3 -c 'import sys; print("{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))')


if [[ $py3version == 3.8.* ]]; then
    printf "Using Python3 version: %s\n" $py3version
    PYTHON=python3
    PIP=pip3.8
elif [[ $py3version == 3.7.* ]]; then
    printf "Using Python3 version: %s\n" $py3version
    PYTHON=python3
    PIP=pip3.7
else
    echo "Exiting. Make sure Python version is 3.8 or 3.7"
    return 1
fi

$PYTHON -m virtualenv --version
if [ $? -ne 0 ]; then
    # Install virtual env
    echo "Virtualenv not detected, running $PIP install virtualenv.  If you don't have $PIP, run easy_install $PIP"
    $PIP install virtualenv
    #return 1
fi

currentdir=`pwd`
export PATH=$PATH:/usr/local/bin:/usr/local/go/bin

# Setup virtual env
virtualenv -p $PYTHON venv
source venv/bin/activate

# Install PYTHON dependencies
$PIP install -r requirements.txt

# set PYTHON env
export PYTHONPATH=$PYTHONPATH:$currentdir/

export ANSIBLE_CONFIG=$currentdir/ansible.cfg

pip install --upgrade pip==20.1.1
pip install couchbase==3.2.7
pip install importlib-metadata==4.3.0
pip install setuptools==68.0.0
