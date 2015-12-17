import sys
import subprocess

from optparse import OptionParser


if __name__ == "__main__":
    usage = """
    usage: python monitor_sync_gateway.py -e "111.11.111.111:4985,222.22.222.222:4985"
    """

    parser = OptionParser(usage=usage)

    parser.add_option("-e", "", action="store", type="string", dest="endpoints", default=None, help="ips running sync_gateway")
    (opts, args) = parser.parse_args(sys.argv[1:])

    if opts.endpoints is None:
        print("Please specify '-e' endpoints to monitor")
        sys.exit(1)

    vars = "mem:memstats.Alloc,mem:memstats.Sys,mem:memstats.HeapAlloc,mem:memstats.HeapInuse,memstats.NumGC,memstats.PauseTotalNs,memstats.PauseNs,syncGateway_db.channelChangesFeeds,syncGateway_db.document_gets,syncGateway_db.revisionCache_adds,syncGateway_db.revs_added"

    subprocess.call(["expvarmon", "-ports={}".format(opts.endpoints), "-endpoint=/_expvar", "-vars={}".format(vars)])
