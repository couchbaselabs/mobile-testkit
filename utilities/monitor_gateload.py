import sys
import subprocess

from optparse import OptionParser


if __name__ == "__main__":
    usage = """
    usage: python monitor_gateload.py -e "111.11.111.111:9876,222.22.222.222:9876"
    """

    parser = OptionParser(usage=usage)

    parser.add_option("-e", "", action="store", type="string", dest="endpoints", default=None, help="ips running gateload")
    (opts, args) = parser.parse_args(sys.argv[1:])

    if opts.endpoints is None:
        print("Please specify '-e' endpoints to monitor")
        sys.exit(1)

    vars = "gateload.ops.PushToSubscriberInteractive.p95, gateload.ops.PushToSubscriberInteractive.p99,gateload.total_doc_pulled,gateload.total_doc_pushed"

    subprocess.call(["expvarmon", "-ports={}".format(opts.endpoints), "-vars={}".format(vars)])
