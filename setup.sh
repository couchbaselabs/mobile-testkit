#!/usr/bin/env bash
# This script sets up an environment for running mobile testkit tests.
# It checks for Python 3.8/3.7, installs virtualenv, and sets up a virtual environment.

# Ensure we use the correct Python version
PYENV_PYTHON="/Users/couchbase/.pyenv/shims/python3"
export PATH="/Users/couchbase/.pyenv/shims:$PATH"

py3version=$($PYENV_PYTHON -c 'import sys; print("{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))')

if [[ $py3version == 3.8.* || $py3version == 3.7.* ]]; then
    printf "Using Python3 version: %s\n" "$py3version"
    PYTHON=$PYENV_PYTHON
    PIP="$PYTHON -m pip"
else
    echo "Exiting. Make sure Python version is 3.8 or 3.7"
    exit 1
fi

# Check if virtualenv is installed
$PYTHON -m virtualenv --version &>/dev/null
if [ $? -ne 0 ]; then
    echo "Virtualenv not detected. Installing virtualenv..."
    $PIP install --user virtualenv
    if [ $? -ne 0 ]; then
        echo "Failed to install virtualenv. Please check your Python/Pip setup."
        exit 1
    fi
fi

# Set up virtual environment
currentdir=$(pwd)
export PATH=$PATH:/usr/local/bin:/usr/local/go/bin

VENV_DIR="$currentdir/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m virtualenv -p $PYTHON "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Verify Python in the virtual environment
$VENV_DIR/bin/python --version
$VENV_DIR/bin/python -m pip install --upgrade pip
$VENV_DIR/bin/python -m pip install couchbase==3.2.7

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install PYTHON dependencies
$PIP install -r requirements.txt

# set PYTHON env
export PYTHONPATH=$PYTHONPATH:$currentdir/

export ANSIBLE_CONFIG=$currentdir/ansible.cfg


pip install --upgrade pip==20.1.1
/Users/couchbase/.pyenv/shims/python3 -m pip install wheel setuptools==68.0.0
python3 -m pip install couchbase==3.2.7 --no-use-pep517
pip install importlib-metadata==4.3.0
pip install setuptools==68.0.0
