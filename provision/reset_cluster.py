import sys
import os
from optparse import OptionParser

from lib.cluster import Cluster

if __name__ == "__main__":
    usage = """usage: analyze_perf_results.py
    --test-id=<test-id>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--conf",
                      action="store", type="string", dest="conf", default=None,
                      help="name of configuration in conf/ to reset cluster with")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    cluster = Cluster()
    cluster.reset(opts.conf)


