import subprocess
import sys
from provisioning_config_parser import hosts_for_tag

from optparse import OptionParser

if __name__ == "__main__":
    usage = """
    usage: python monitor_sync_gateway.py"
    """

    # Get sync_gateway ips from ansible inventory
    sgs_host_vars = hosts_for_tag("sync_gateways")
    sgs = [sgv["ansible_host"] for sgv in sgs_host_vars]

    if len(sgs) == 0:
        print("No sync_gateways to monitor in 'provisioning_config'")
        sys.exit(1)

    print("Monitoring sync_gateways: {}".format(sgs))
    sgs_with_port = [sg + ":4985" for sg in sgs]
    sgs_joined = ",".join(sgs_with_port)

    expvars = [
        "mem:memstats.Alloc",
        "mem:memstats.Sys",
        "mem:memstats.HeapAlloc",
        "mem:memstats.HeapInuse",
        "memstats.NumGC",
        "memstats.PauseTotalNs",
        "memstats.PauseNs",
        "syncGateway_db.channelChangesFeeds",
        "syncGateway_db.document_gets",
        "syncGateway_db.revisionCache_adds",
        "syncGateway_db.revs_added"
    ]

    expvars_combined = ",".join(expvars)

    subprocess.call(["expvarmon",
                     "-ports={}".format(sgs_joined),
                     "-endpoint=/_expvar",
                     "-vars={}".format(expvars_combined)])
