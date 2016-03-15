import subprocess
import sys
from optparse import OptionParser

usage = "usage: python teardown_cluster.py -n <stack_name>"

parser = OptionParser(usage=usage)

parser.add_option("-n", "--stackname",
                  action="store", type="string", dest="stackname", default=None,
                  help="stackname of cloudformation cluster to delete")

arg_parameters = sys.argv[1:]

(opts, args) = parser.parse_args(arg_parameters)

if opts.stackname is None:
    print("Please provide a stackname to teardown")
    sys.exit(1)

subprocess.call(["aws", "cloudformation", "delete-stack", "--stack-name", opts.stackname, "--region", "us-east-1"])
