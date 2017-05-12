
import subprocess
import os
from run_scripts.test_batch import TEST_BATCH, SYNC_GATEWAY_VERSION_OR_COMMIT, SERVER_VERSION
import argparse

"""

This runs a batch of tests defined in a separate file.

To use this:

   - cp run_scripts/test_batch.py.example run_scripts/test_batch.py
   - python run_sg_test_batch.py --help

"""


def run_tests(abort_on_fail=False):

    # The current provisioned test suite
    provisioned_test_suite = ""

    for test in TEST_BATCH:
        suite = test["suite"]
        testname = test["testname"]
        mode = test["mode"]

        print "------------------------------------------------- Running test: suite: {}, testname: {}".format(suite, testname)

        cmd_args = [
            "pytest",
            "-s",
            "--mode={}".format(mode),
        ]

        if suite == provisioned_test_suite:
            print "Skipping provisioning"
            cmd_args += [ "--skip-provisioning" ]
        else:
            print "--------------------------------------------- Provisioning test: suite: {}, testname: {}".format(suite, testname)
            # force provisioning and record this as the provisioned_test_suite
            cmd_args += [
                "--server-version={}".format(SERVER_VERSION),
                "--sync-gateway-version={}".format(SYNC_GATEWAY_VERSION_OR_COMMIT),
            ]

            provisioned_test_suite = suite

        cmd_args += [
            "-k",
            testname,
            suite
        ]

        print "cmd_args: {}".format(cmd_args)
        cmd = " ".join(cmd_args)
        print("Command: {}".format(cmd))
        raw_exit_val = os.system(cmd)
        exit_code = os.WEXITSTATUS(raw_exit_val)
        if abort_on_fail == True and exit_code != 0:
            raise Exception("Test failed, aborting")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--abort-on-fail', help='Abort batch test run on first test failure', action='store_true')
    args = parser.parse_args()

    run_tests(args.abort_on_fail) 