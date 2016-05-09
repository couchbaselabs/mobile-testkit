# This scripts attempts to setup an environment for running mobile testkit tests.
# 1. Check that you have Python 2.7 and virtualenv installed
# 2. Installs venv/ in this directory containing a python 2.7 interpreter
# 3. Installs all pip packages required by this repo
# 4. Adds custom library paths to your PYTHONPATH

version=$(python -c 'import sys; print "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)')

if [[ $version == 2.7.* ]]; then
    printf "Using Python version: %s\n" $version
else
    echo "Exiting. Make sure Python version is 2.7."
    exit 1
fi

python -m virtualenv --version
if [ $? -ne 0 ]; then
    # Install virtual env
    "You need to 'pip install virtualenv' on the machine running tests"
    exit 1
fi

currentdir=`pwd`

# Setup virtual env
virtualenv -p python venv
source venv/bin/activate

# Install python dependencies
pip install -r requirements.txt

# set python env
export PYTHONPATH=$PYTHONPATH:$currentdir/
export PYTHONPATH=$PYTHONPATH:$currentdir/libraries/
export PYTHONPATH=$PYTHONPATH:$currentdir/libraries/data
export PYTHONPATH=$PYTHONPATH:$currentdir/libraries/testkit
export PYTHONPATH=$PYTHONPATH:$currentdir/libraries/provision
export PYTHONPATH=$PYTHONPATH:$currentdir/libraries/utilities
