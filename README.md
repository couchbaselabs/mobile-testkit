
This repository contains Mobile QE Functional / Integration tests. 

```
$ git clone https://github.com/couchbaselabs/mobile-testkit.git
$ cd mobile-testkit/
```


Table of Contents
=================

* [Repo Structure](#repo-structure)
* [Repo Dependencies](#repo-dependencies)
* [Development Environment](#development-environment)
* [Listener Tests](#listener-tests)
* [sync_gateway Tests](#sync_gateway-tests)
* [sync_gateway Performance Tests](#sync_gateway-peftests)
* [Debugging](#debugging)
* [Monitoring](#monitoring)
* [Running Mobile-Testkit Framework Unit Tests](#running-mobile-testkit-framework-unit-tests)
* [Setting up Google Emulators](#setting-up-google-emulators)
* [Windows Setup for Ansible](#windows-setup-for-ansible)
* [Known Issues And Limitations](#known-issues-and-limitations)


Repo Structure
==============

The repo structure is the following:

* libraries
 * keywords (new devopement, will be renamed to testkit in the near future)
 * provision
 * testkit (legacy)
 * utilities

* testsuites
 * listener
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

**Install libcouchbase**

On MacOSX
```
$ brew install libcouchbase
```

On CentOS7
```
$ yum install gcc libffi-devel python-devel openssl-devel
```

```
$ yum install -y libev libevent
$ wget http://packages.couchbase.com/clients/c/libcouchbase-2.5.6_centos7_x86_64.tar && \
    tar xvf libcouchbase-2.5.6_centos7_x86_64.tar && \
    cd libcouchbase-2.5.6_centos7_x86_64 && \
    rpm -ivh libcouchbase-devel-2.5.6-1.el7.centos.x86_64.rpm \
             libcouchbase2-core-2.5.6-1.el7.centos.x86_64.rpm \
	     libcouchbase2-bin-2.5.6-1.el7.centos.x86_64.rpm \
	     libcouchbase2-libevent-2.5.6-1.el7.centos.x86_64.rpm && \
    rm -f *.rpm	     
```

**Set up virtualenv install python dependencies**

```
$ [sudo] pip install virtualenv
```

```
$ cd mobile-testkit/
```

Setup PATH, PYTHONPATH, and ANSIBLE_CONFIG
```
source setup.sh
```

If you plan on doing development, it may be helpful to add the PYTHONPATH env variables to your .bashrc file so that you do not have to run this setup everytime you open a new shell.

### Development Environment

You may use what ever environment you would like, however [PyCharm](https://www.jetbrains.com/pycharm/) is a very good option. There are a couple steps required to get going with this IDE if you choose to use it. 

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

Now PyCharm should recognize the custom libraries and provide intellisense.

Listener Tests
==============

The listener tests are a series of tests utilizing Couchbase Lite Listener and Sync Gateway or P2P. They are meant to be cross platform and should be able to run for
for all the platforms that expose the Listener (Mac OSX, .NET, Android, iOS)

### Dependencies

Android SDK. Download [Android Studio](http://developer.android.com/sdk/index.html) to install

```
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH
```

Mono to execute LiteServ .NET on macosx
```
http://www.mono-project.com/docs/getting-started/install/mac/
```

Install libimobiledevice for capture device logging for iOS
```
$ brew install --HEAD libimobiledevice
$ brew install ideviceinstaller
```
Install ios-deploy to bootstrap install / lauching of iOS apps
```
brew install node
npm install -g ios-deploy
```

The Listener is exposed via a LiteServ application which will be downloaded and launched when running the test.

NOTE: For running with Android, you must be running an emulator or device. The easiest is Genymotion with NAT,
however devices are supported as long the sync_gateway and the android device can communicate. 

Make sure to set up vm cluster [Spin Up Machines on Vagrant](#spin-up-machines-on-vagrant)

### Listener Test Excecution (Client + Client (P2P))
================================

[Running Tests](testsuites/listener/shared/client_client/README.md) 

### Listener Test Excecution (Client + SG)
================================

[Running Tests](testsuites/listener/shared/client_sg/README.md) 


sync_gateway Tests
==================

### sync_gateway Test Dependencies
==================================

The sync_gateway tests require targeting different cluster topologies of sync_gateway(s) + Couchbase Server(s). Don't worry! We will set this up for you. There are two options for these cluster nodes. You can use EC2 AWS instances or vms.

NOTE: This is currently only running on CentOS 7. 

## AWS Environment requirements

You will need an access key and secret access key. [This guide](http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html) explains how to get them from your AWS account.

Then you will need an AWS keypair. [This guide](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html#how-to-generate-your-own-key-and-import-it-to-aws) explains how to import your own Key Pair to Amazon EC2. Mobile-testkit creates a key-pair in the us-east region so the key pair must be set on this region too.

- Add boto configuration
    ```
    $ cd ~/ 
    $ touch .boto
    $ vi .boto
    ```
    #### IMPORTANT: Do not check in the information below

- Add your AWS credentials (Below are a fake example).
    ```
    [Credentials]
    aws_access_key_id = CDABGHEFCDABGHEFCDAB
    aws_secret_access_key = ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
    ```

- Add AWS env variables
    ```
    $ export AWS_ACCESS_KEY_ID=CDABGHEFCDABGHEFCDAB
    $ export AWS_SECRET_ACCESS_KEY=ABGHEFCDABGHEFCDABGHEFCDABGHEFCDABGHEFCDAB
    $ export AWS_KEY=<your-aws-keypair-name>
    ```

You probably want to persist these in your `~/.bash_profile`.

The sync_gateway tests use [Ansible](https://www.ansible.com/) to provision the clusters.  

**Setup Global Ansible Config**

```
$ cp ansible.cfg.example ansible.cfg
$ vi ansible.cfg  # edit to your liking
```

Make sure to use your ssh user ("root" is default). If you are using AWS, you may have to change this to "centos"

**Create pool.json file**

This is the list of machines that is used to generate the resources/cluster_configs which are used by the functional tests.

*Create a pool.json of endpoints you would like to target (IPs or AWS ec2 endpoints)* 
- Rename resources/pool.json.example -> resources/pool.json. Update the fake ips with your endpoints or EC2 endpoints.
- If you do not have IP endpoints and would like to use Vagrant (easiest), see [Spin up Machines on Vagrant](#spin-up-machines-on-vagrant)
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
python libraries/utilities/generate_clusters_from_pool.py
```
This targets the 'resources/pool.json' you supplied above and generates cluster definitions required for provisioning and running the tests. The generated configurations can be found in 'resources/cluster_configs/'.

- Provision the cluster with --install-deps flag (only once)

- Set the `CLUSTER_CONFIG` environment variable that is required by the `provision_cluster.py` script.  Eg: `$ export CLUSTER_CONFIG=resources/cluster_configs/2sg_1cbs`

- Install the dependencies:
```
python libraries/provision/install_deps.py
```

- Install sync_gateway package:

```
$ python libraries/provision/provision_cluster.py \
    --server-version=4.1.1 \
    --sync-gateway-version=1.2.0-79
```

- OR Install sync_gateway source:

Since building Sync Gateway from source requires access to the private sync-gateway-accel repo, you will need to
be in possession of the appropriate [SSH key](http://cbmobile-sharedkeys.s3.amazonaws.com/cbmobile_private_repo_read_only).
See `install-gh-deploy-keys.py` for more info.

```
$ python libraries/utilities/install-gh-deploy-keys.py
    --key-path=/path/to/cbmobile_private_repo_read_only_key
    --ssh-user=vagrant
$ python libraries/provision/provision_cluster.py \
    --server-version=4.1.1 \
    --sync-gateway-commit=062bc26a8b65e63b3a80ba0f11506e49681d4c8c (requires full commit hash)
```

If you experience ssh errors, you may need to verify that the key has been added to your ssh agent

```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/sample_key
```


### sync_gateway Test Excecution
================================

[Running Functional Tests](testsuites/syncgateway/functional/tests/README.md) 



### Spin Up Machines on Vagrant
===============================

NOTE: This has only been tested on Mac OSX

1. Install VirtualBox - https://www.virtualbox.org/wiki/Downloads
1. Install Vagrant - https://www.vagrantup.com/downloads.html
1. `cd` into `vagrant/private_network` (or `vagrant/public_network` if you need VM's exposed to LAN, for example when testing against actual mobile devices)

Create cluster with private network

`vagrant up`

1. Run `python utilities/generate_cluster_configs_from_vagrant_hosts.py --private-network|public-network` 
    - This will discover running vagrant boxes and get their ips
    - Generate `resources/pool.json`
    - Generate `resources/cluster_configs/`
1. Create an ssh key. `cd ~/.ssh/ && ssh-keygen`
1. Make sure you have PasswordAuthentication set on each vagrant instance
```
cd vagrant/private_network/ && vagrant ssh host1
$ [root@localhost vagrant]# sudo bash
$ [root@localhost vagrant]# vi /etc/ssh/sshd_config 

...

# To disable tunneled clear text passwords, change to no here!
#PasswordAuthentication yes
#PermitEmptyPasswords no
PasswordAuthentication yes

...

$ [root@localhost vagrant]# service sshd restart
$ Redirecting to /bin/systemctl restart  sshd.service
```
Do the same for rests of the hosts in the `Vagrantfile`

1. Install the ssh key into the machines via 

```
python libraries/utilities/install_keys.py --key-name=id_rsa.pub --ssh-user=vagrant
```

use the password `vagrant`. 

1. Create `ansible.cfg` 
```
$ cp ansible.cfg.example ansible.cfg
$ vi ansible.cfg  # edit to your liking
```
1. Edit `ansible.cfg` and change the user to 'vagrant'
1. Set the `CLUSTER_CONFIG` environment variable that is required by the `provision_cluster.py` script.  Eg: `$ export CLUSTER_CONFIG=resources/cluster_configs/1sg`
1. Install the dependencies
```
python libraries/provision/install_deps.py
```
1. Provision the cluster
```
python libraries/provision/provision_cluster.py --server-version=4.5.0 --sync-gateway-version=1.3.1-16
```

Enjoy! You now have a Couchbase Server + Sync Gateway cluster running on your machine!

### Spin Up Machines on AWS
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

Wait until the resources are up, then create the `pool.json` file by hand according to instructions above.


Debugging
=========

Thanks to pytest, you can break into pdb very easily

```
import pdb

for thing in things:
    pdb.set_trace()
    # break here ^
    thing.do()
```

If you want the test to drop into pdb at the point of failure, you can execute the test with the flag

```
pytest --pdb
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

Running Mobile-Testkit Framework Unit Tests
===========================================

Below is an example on how to run mobile testkit framework unit tests

```
pytest libraries/provision/test_install_sync_gateway.py
```

sync_gateway Perf Tests
=======================

**Running Performance Tests**

- [Spin up a AWS CloudFormation stack](#Spin=Up-Machines-on-AWS)

- Generate a pool.json

```
python libraries/provision/generate_pools_json_from_aws.py --stackname=TleydenPerfSyncGw12 --targetfile=resources/pool.json
```

- Generate clusters from pool

This will create the `2sg_3cbs_2lgs` and `2sg_3cbs_2lgs.json` cluster config that is used for performance testing

```
python libraries/utilities/generate_clusters_from_pool.py
```

- Set CLUSTER_CONFIG

```
export CLUSTER_CONFIG=resources/cluster_configs/2sg_3cbs_2lgs
```

- Provision cluster and install dependencies

```
python libraries/provision/provision_cluster.py --install-deps --server-version 4.1.1 --sync-gateway-version 1.3.0-274 
```

- Run tests

```
python testsuites/syncgateway/performance/run_perf_test.py --number-pullers 1000 --number-pushers 1000 --use-gateload --test-id 1 --sync-gateway-config-path resources/sync_gateway_configs/performance/sync_gateway_default_performance_cc.json
```

Setting up Google Emulators
===========================
* Open Android Studio
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


Windows Setup for Ansible
=========================
- Follow instructions here - http://docs.ansible.com/ansible/intro_windows.html

- Create an inventory similar to - 
```
[windows]
win1 ansible_host=111.22.333.444

[windows:vars]
# Use your RDP / local windows user credentials for ansible_user / ansible_password
ansible_user=FakeUser
ansible_password=FakePassword
ansible_port=5986
ansible_connection=winrm
# The following is necessary for Python 2.7.9+ when using default WinRM self-signed certificates:
ansible_winrm_server_cert_validation=ignore
```
Save as `resources/cluster_configs/windows`

### IMPORTANT: Do not publish or check this inventory file in. If you do, anyone could potentially access your machine.

- Download and execute this in the windows target PowerShell (Run as Administrator)
[ConfigureRemotingForAnsible.ps1](https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1)
```
.\ConfigureRemotingForAnsible.ps1 -SkipNetworkProfileCheck
```

If you hit errors, you may have to allow unsigned script execution (Use with caution)
```
Set-ExecutionPolicy Unrestricted
```

Test by:
```
ansible windows -i resources/cluster_configs/windows -m win_ping
```


Known Issues And Limitations
============================

