## Overview

This directory contains code pertaining to this Jenkins build:

http://uberjenkins.sc.couchbase.com/view/Performance/job/sgload-perf-test/

It takes the approach of having most of the build script code in python rather than bash so it can be reused across Jenkins job more easily.  For example, a gateload-perf-test could re-use this code but kick off gateload instead of sgload.

## Direnv

This uses [direnv](https://direnv.net/) to setup the environment expected by the script, which is usually provided by Jenkins.

```
$ brew install direnv
```

## Running 


```
$ cp .envsrc-example .envsrc
$ cd .. && cd continuous_integration
```

At this point you will be prompted to allow `direnv` to source the environment.  You will need to allow it to do so.

```
$ python sgload_perf_test.py
```

You will get errors about a missing `ansible.cfg.example` because the script expects to be run from the parent directory.  This is a work in progress.  I guess in the meantime, you can copy your `.envsrc` up to the parent directory and run from there.  