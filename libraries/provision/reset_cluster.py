import sys
import os
from optparse import OptionParser

from testkit.cluster import Cluster

if __name__ == "__main__":
    usage = """usage: reset_cluster.py
    --cong=<name-of-conf>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--conf",
                      action="store", type="string", dest="conf", default=None,
                      help="name of configuration in conf/ to reset cluster with")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    cluster = Cluster()
    cluster.reset(opts.conf)


