
This repository contains Mobile QE Functional / Integration tests. 

```
$ git clone https://github.com/couchbaselabs/mobile-testkit.git
```

The mobile test suites leverage Robot Framework (http://robotframework.org/) as an organization platform as well as a test runner and reporter. 


Table of Contents
=================

* [Repo Structure](#repo-structure)
* [Repo Dependencies](#repo-dependencies)
* [Development Environment](#development-environment)
* [Android Tests](#android-tests)
* [GrocerySync Tests](#grocerysync-tests)
* [iOS Tests](#ios-tests)
* [NET Tests](#net-tests)
* [sgcollectinfo Tests](#sgcollectinfo-tests)
* [sync_gateway Tests](#sync_gateway-tests)
* [Monitoring](#monitoring)
* [Known Issues And Limitations](#known-issues-and-limitations)


Repo Structure
==============

The repo is organized as following

* libraries
 * provision
 * testkit
 * utilities

* testsuites
 * android
 * grocerysync
 * ios
 * net
 * sgcollectinfo
 * syncgateway


Repo Dependencies
=================

## Setup Controller on OSX

The "controller" is the machine that runs the tests and communicates with the system under test, which is typically:

* Your developer workstation
* A virtual machine / docker container

The instructions below are for setting up directly on OSX.  If you prefer to run this under Docker, see the [Running under Docker](https://github.com/couchbaselabs/mobile-testkit/wiki/Running-under-Docker) wiki page.

**Install Python via brew**

If you are on OSX El Capitan, you must install python via brew rather than using the system python due to [Pip issue 3165](https://github.com/pypa/pip/issues/3165).

```
$ brew install python
```

After you install it, you should see that the python installed via brew is the default python:

```
$ which python
/usr/local/bin/python
$ python --version
Python 2.7.10
```

**Set up virtualenv install python dependencies**

```
$ [sudo] pip install virtualenv
```

```
$ cd mobile-testkit/
$ virtualenv -p /usr/bin/python2.7 venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

** Add current directory to $PYTHONPATH. This will pick the custom libraries and allow you to use them

```
$ export PYTHONPATH=$PYTHONPATH:.
```

### Development Environment
===========================
You may use what ever environment you would like, however PyCharm [PyCharm](https://www.jetbrains.com/pycharm/) is very good option. There are a couple steps required to get going with this IDE if you choose to use it. 

**Set Interpreter and Library Home**
- Go to PyCharm -> Preferences
- Expand Project: mobile-testkit and select Project Interpreter
- From the dropdown, make sure your venv (created above) is selected
- Click Apply
- Click on the gear next to the interpreter
- Select More ...
- Make sure your virtualenv is selected and click on the directory icon on the bottom (Show Paths for Selected Interpreter)
- Click the plus icon and find the path to mobile-testkit/
- Select libraries from inside the repo directory
- Click OK, OK, Apply

Now PyCharm should recognize the custom libraries and provide intellisense

Android Tests
===============

### Android Test Dependencies
=============================

* Android SDK. Download [Android Studio](http://developer.android.com/sdk/index.html) to install
    * API 23
    * API 22
    * Android SDK Build-tools 22.0.1
* Monkeyrunner (ships with Android Studio, must be in your PATH). You will need this to bootstrap apk installation on your emulators. Test by executing:

You will need this to bootstrap apk installation on your emulators.

```
$ monkeyrunner
```

You should see something similar to the output below

```
Jython 2.5.3 (2.5:c56500f08d34+, Aug 13 2012, 14:54:35)
[Java HotSpot(TM) 64-Bit Server VM (Oracle Corporation)] on java1.7.0_79
>>>
```
Ctrl+D to escape 


```
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH
```

### Create Android Emulator (AVD)

* Create new "dummy" project
* Click on AVD manager (purple icon)
* Create Virtual Device
* Click "Download" next to Marshmallow x86_64
* Hit Next/Finish to create it

The scenarios can run on Android stock emulators/Genymotion emulators and devices.

If you're running Android stock emulators you should make sure they are using HAXM. Follow the instructions here to install (https://software.intel.com/en-us/android/articles/installation-instructions-for-intel-hardware-accelerated-execution-manager-mac-os-x).

Ensure the RAM allocated to your combined running emulators is less than the total allocated to HAXM. You can configure the RAM for your emulator images in the Android Virtual Device Manager and in HAXM by reinstalling via the .dmg in the android sdk folder.
 
To run the tests make sure you have lauched the correct number of emulators. You can launch them using the following command. 
```
emulator -scale 0.25 @Nexus_5_API_23 &
emulator -scale 0.25 @Nexus_5_API_23 &
emulator -scale 0.25 @Nexus_5_API_23 &
emulator -scale 0.25 @Nexus_5_API_23 &
emulator -scale 0.25 @Nexus_5_API_23 &
```
Verify that the names listed below match the device definitions for the test you are trying to run
```
adb devices -l
```
```
List of devices attached
emulator-5562          device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
emulator-5560          device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
emulator-5558          device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
emulator-5556          device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
emulator-5554          device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
```

Most of the port forwarding will be set up via instantiation of the Listener. However, you do need to complete some additional steps.

**Note:** Instantiating a Listener in `test_listener_rest.py` will automatically forward the port the listener is running on to one on localhost. However, that port forwarding will not be bound on the local IP of your computer. This can be useful when combining actual devices and emulators. The following section describes how to make the emulators reachable from devices.

Once you have emulators and possibly port forwarding setup, set the `P2P_APP` environment variable to the `.apk` of the application to be tested.

```
$ export P2P_APP=/path/to/apk
```

If the test fails with a hostname unreachable error then it's probably because port forwarding needs to be configured (read section below).

### Port forwarding (setup once)

Add the following lines to the file `/etc/sysctl.conf`
```
net.inet.ip.forwarding=1
net.inet6.ip6.forwarding=1
```

Specifying the 'local_port' when instantiating a Listener will forward the port on localhost only.
 
 We need to bind the port on the `en0` interface to be reachable on the Wi-Fi. On Mac, this can be done with `pfctl`. Create a new anchor file under `/etc/pf.anchors/com.p2p`:

```
rdr pass on lo0 inet proto tcp from any to any port 10000 -> 127.0.0.1 port 10000
rdr pass on en0 inet proto tcp from any to any port 10000 -> 127.0.0.1 port 10000

rdr pass on lo0 inet proto tcp from any to any port 11000 -> 127.0.0.1 port 11000
rdr pass on en0 inet proto tcp from any to any port 11000 -> 127.0.0.1 port 11000
...

```
Parse and test your anchor file to make sure there a no errors:
```
sudo pfctl -vnf /etc/pf.anchors/com.p2p
```

The file at `/etc/pf.conf` is the main configuration file that `pf` loads at boot. Make sure to add both lines below to `/etc/pf.conf`:

```
scrub-anchor "com.apple/*"
nat-anchor "com.apple/*"
rdr-anchor "com.apple/*"
rdr-anchor "com.p2p"      # Port forwading for p2p replications 
dummynet-anchor "com.apple/*"
anchor "com.apple/*"
load anchor "com.apple" from "/etc/pf.anchors/com.apple"
load anchor "com.p2p" from "/etc/pf.anchors/com.p2p"     # Port forwarding for p2p replications
```

The `lo0` are for local requests, and the `en0` entries are for external requests (coming from an actual device or another emulator targeting your host).

Next, load and enable `pf` by running the following:

```
$ sudo pfctl -ef /etc/pf.conf
```

Now, all the databases are reachable on the internal network via host:forwarded_port (ex. http://192.168.0.21:10000/db), where 192.168.0.21 is your host computer's ip and 10000 is the 'local_port' passed when instantiating the Listener.


### Android Test Excecution
===========================
To run the tests
```
$ robot testsuites/android/listener/
```

GrocerySync Tests
=================

### GrocerySync Test Dependencies
=================================

The GrocerySync tests use [Appium](http://appium.io/) under the hood.

```
$ brew install node
$ npm install -g appium
```


### GrocerySync Test Excecution
===============================
TODO


iOS Tests
=========
TODO

### iOS Test Dependencies
=========================
TODO

### iOS Test Excecution
=======================
TODO

NET Tests
=========
TODO

### NET Test Dependencies
=========================
TODO

### NET Test Excecution
=======================
TODO

sgcollectinfo Tests
===================
TODO

### sgcollectinfo Test Dependencies
===================================
TODO

### sgcollectinfo Test Excecution
=================================
TODO

sync_gateway Tests
==================

### sync_gateway Test Dependencies
==================================

The sync_gateway tests require targeting different cluster topologies of sync_gateway(s) + Couchbase Server(s). Don't worry! We will set this up for you. There are two options for these cluster nodes. You can use EC2 AWS instances or vms. 

NOTE: This is currently only running on CentOS 7. 

** AWS Environment requirements

* Add boto configuration

```
$ cd ~/ 
$ touch .boto
$ vi .boto
```

#### IMPORTANT: Do not check in the information below

**Add your AWS credentials (Below are a fake example).**

```
[Credentials]
aws_access_key_id = CDABGHEFCDABGHEFCDAB
aws_secret_access_key = ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
```

**Add AWS env variables**

```
$ export AWS_ACCESS_KEY_ID=CDABGHEFCDABGHEFCDAB
$ export AWS_SECRET_ACCESS_KEY=ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
$ export AWS_KEY=<your-aws-keypair-name>
$ export KEYNAME=key_<your-aws-keypair-name>
```

You probably want to persist these in your `~/.bash_profile`.

The sync_gateway tests use [Ansible](https://www.ansible.com/) to provision the clusters.  

**Setup Global Ansible Config**

```
$ cd libraries/provision/ansible/playbooks
$ cp ansible.cfg.example ansible.cfg
$ vi ansible.cfg  # edit to your liking
```

Make sure to use your ssh user ("root" is default). If you are using AWS, you may have to change this to "centos"

**Spin up VM's or Bare Metal machines**

*Create a pool.json of endpoints you would like to target (IPs or AWS ec2 endpoints)* 
- Rename resources/pool.json.example -> resources/pool.json. Update the fake ips with your endpoints or EC2 endpoints.
- If you do not have IP endpoints and would like to use AWS, see [Spin up Machines on AWS](#spin-up-machines-on-aws)
- Make sure you have at least 4 unique endpoints
- If you are using vms and do not have key access for ssh, you can use the key installer script (Not required for AWS). This will target 'resources/pool.json' and attempt to deploy a public key of your choice to the machines.

In order to use Ansible, the controller needs to have it's SSH keys in all the hosts that it's connecting to.  

Follow the instructions in [Docker container SSH key instructions](https://github.com/couchbaselabs/mobile-testkit/wiki/Docker-Container---SSH-Keys) to setup keys in Docker

```
python libraries/utilities/install_keys.py --key-name=sample_key.pub --ssh-user=root
```
- Generate the necessary cluster topologies to run the tests
```
python libraries/utilities/generate_clusters_from_pool.py`
```
This targets the 'resources/pool.json' you supplied above and generates cluster definitions required for provisioning and running the tests. The generated configurations can be found in 'resources/cluster_configs/'.

- Provision the cluster with --install-deps flag (only once)

- Install sync_gateway package:

```
$ python libraries/provision/provision_cluster.py \
    --server-version=4.1.0 \
    --sync-gateway-version=1.2.0-79
    --install-deps (first time only, this will install prerequisites to build / debug)
```

- OR Install sync_gateway source:

```
$ python libraries/provision/provision_cluster.py \
    --server-version=4.1.0 \
    --sync-gateway-branch=master
    --install-deps (first time only, this will install prerequisites to build / debug)
```

If you experience ssh errors, you may need to verify that the key has been added to your ssh agent

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/sample_key
```


### sync_gateway Test Excecution
================================

**Running Functional Tests**

Run the whole suite 

`robot -b debug.txt -v SERVER_VERSION:4.1.0 -v SYNC_GATEWAY_VERSION:1.2.0-79 testsuites/syncgateway/functional/ `

Run a single suite  

`robot -b debug.txt -v SERVER_VERSION:4.1.0 -v SYNC_GATEWAY_VERSION:1.2.0-79 testsuites/syncgateway/functional/1sg_1cbs.robot`

Run a single test   

`robot -b debug.txt -v SERVER_VERSION:4.1.0 -v SYNC_GATEWAY_VERSION:1.2.0-79 -t "test bulk get compression no compression" testsuites/syncgateway/functional/1sg_1cbs.robot`

Although it is not necessary, the `-b debug.txt` will provide more output and stacktraces for deeper investigation

**Running Performance Tests**

- [Spin up a AWS CloudFormation stack](#Spin=Up-Machines-on-AWS)

- Edit 'aws_config' to reflect the number of writers you require
- 
- Run the performance tests

```
robot testsuites/syncgateway/performance/minimatrix.robot
```

- Teardown the CloudFormation Stack

```
python libraries/provision/teardown_cluster.py --stackname="TestPerfStack
```

Monitoring
==========

**Monitoring Clusters**

Make sure you have installed expvarmon 
```
go get github.com/divan/expvarmon
```

To monitor the Gateload expvars for [load_generators] nodes in the cluster_config 
```
python libraries/utilities/monitor_gateload.py
```

To monitor the sync_gateway expvars for [sync_gateways] nodes in the cluster_config 
```
python libraries/utilities/monitor_sync_gateway.py
```

**Collecting Sync Gateway logs**

```
$ python libraries/utilities/fetch_sg_logs.py
```




## Spin Up Machines on AWS
==========================
1. Create and AWS CloudFormation Stack. Make sure you have set up AWS credentials described in [sync_gateway Test Dependencies](#sync_gateway-Test-Dependencies)

```
$ python libraries/provision/create_and_instantiate_cluster.py \
    --stackname="YourCloudFormationStack" \
    --num-servers=1 \
    --server-type="m3.large" \
    --num-sync-gateways=2 \
    --sync-gateway-type="m3.medium" \
    --num-gatlings=1 \
    --gatling-type="m3.medium" \
    --num-lbs=0 \
    --lb-type="m3.medium" 
```

Wait until the resources are up, then

2. Generate an ansible inventory from your CloudFormation Stack. The generated 'aws_config' file will be written to 'resources/cluster_configs'

```
python libraries/provision/generate_ansible_inventory_from_aws.py --stackname="TestPerfStack" --targetfile="aws_config"
```

## Known Issues And Limitations
============================
- This repo now only supports ansible 2.0.0.2. There are known issues with certain versions of ansible.
