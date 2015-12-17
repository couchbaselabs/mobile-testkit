import os
import subprocess
import sys
from optparse import OptionParser
from lib.cluster import Cluster

import generate_gateload_configs

def run_tests(number_pullers, number_pushers, use_gateload, gen_gateload_config):
    if use_gateload:
        print "Using Gateload"
        print ">>> Starting gateload with {0} pullers and {1} pushers".format(number_pullers, number_pushers)

        if int(number_pullers) > 0 and not gen_gateload_config:
            raise Exception("You specified --num-pullers but did not set --gen-gateload-config")
            

        os.chdir("performance_tests/ansible/playbooks")

        # Build gateload
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "build-gateload.yml"])

        # Generate gateload config
        if gen_gateload_config:
            generate_gateload_configs.main(number_pullers, number_pushers)

        # Start gateload
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "start-gateload.yml"])

    else:
        print "Using Gatling"
        print ">>> Starting gatling with {0} pullers and {1} pushers".format(number_pullers, number_pushers)
        os.chdir("performance_tests/ansible/playbooks")

        # Configure gatling
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "configure-gatling.yml"])

        # Run Gatling
        subprocess.call([
            "ansible-playbook", 
            "-i", "../../../provisioning_config",
            "run-gatling-theme.yml",
            "--extra-vars", "number_of_pullers={0} number_of_pushers={1}".format(number_pullers, number_pushers)
        ])

if __name__ == "__main__":
    usage = """usage: run_tests.py
    --number-pullers=<number_pullers>
    --number-pushers<number_pushers>
    --reset-sync-gw
    --use-gateload
    --gen-gateload-config
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--number-pullers",
                      action="store", type="string", dest="number_pullers", default=8000,
                      help="number of pullers")

    parser.add_option("", "--number-pushers",
                      action="store", type="int", dest="number_pushers", default=5000,
                      help="number of pushers")

    parser.add_option("", "--use-gateload",
                      action="store_true", dest="use_gateload", default=False,
                      help="flag to set to use gateload")

    parser.add_option("", "--gen-gateload-config",
                      action="store_true", dest="gen_gateload_config", default=False,
                      help="flag to set to generate gateload config")

    parser.add_option("", "--reset-sync-gw",
                      action="store_true", dest="reset_sync_gateway", default=False,
                      help="reset CBS buckets, delete SG logs, restart SG")


    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.reset_sync_gateway:
        print "Resetting Sync Gateway"
        cluster = Cluster()
        cluster.reset("performance/sync_gateway_default_performance.json")

    run_tests(
        number_pullers=opts.number_pullers,
        number_pushers=opts.number_pushers,
        use_gateload=opts.use_gateload,
        gen_gateload_config=opts.gen_gateload_config
    )
