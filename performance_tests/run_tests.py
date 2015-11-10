import os
import subprocess
import sys
from optparse import OptionParser


def run_tests(number_pullers, number_pushers, use_gateload):
    if use_gateload:
        print "Using Gateload"
        print ">>> Starting gateload with {0} pullers and {1} pushers".format(number_pullers, number_pushers)

        os.chdir("ansible/playbooks")

        # Build gateload
        subprocess.call(["ansible-playbook", "-i", "../../../temp_ansible_hosts", "build-gateload.yml"])

        # Start gateload
        subprocess.call(["ansible-playbook", "-i", "../../../temp_ansible_hosts", "start-gateload.yml"])

    else:
        print "Using Gatling"
        print ">>> Starting gatling with {0} pullers and {1} pushers".format(number_pullers, number_pushers)
        os.chdir("ansible/playbooks")

        # Configure gatling
        subprocess.call(["ansible-playbook", "-i", "../../../temp_ansible_hosts", "configure-gatling.yml"])

        # Run Gatling
        subprocess.call([
            "ansible-playbook", 
            "-i", "../../../temp_ansible_hosts",
            "run-gatling-theme.yml",
            "--extra-vars", "number_of_pullers={0} number_of_pushers={1}".format(number_pullers, number_pushers)
        ])

if __name__ == "__main__":
    usage = """usage: run_tests.py
    --number-pullers=<number_pullers>
    --number-pushers<number_pushers>
    --use-gateload"""

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

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)



    run_tests(
        number_pullers=opts.number_pullers,
        number_pushers=opts.number_pushers,
        use_gateload=opts.use_gateload
    )
