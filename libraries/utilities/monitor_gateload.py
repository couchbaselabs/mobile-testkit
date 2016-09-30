import subprocess
import sys
import os
from provisioning_config_parser import hosts_for_tag

from keywords.utils import log_info

if __name__ == "__main__":
    usage = """
    usage: python monitor_gateload.py"
    """

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    # Get gateload ips from ansible inventory
    lgs_host_vars = hosts_for_tag(cluster_conf, "load_generators")
    lgs = [lg["ansible_host"] for lg in lgs_host_vars]

    if len(lgs) == 0:
        print("No gateloads to monitor in 'provisioning_config'")
        sys.exit(1)

    print("Monitoring gateloads: {}".format(lgs))
    lgs_with_port = [lg + ":9876" for lg in lgs]
    lgs_joined = ",".join(lgs_with_port)

    expvars = [
        "gateload.ops.PushToSubscriberInteractive.p95",
        "gateload.ops.PushToSubscriberInteractive.p99",
        "gateload.total_doc_pulled",
        "gateload.total_doc_pushed",
        "gateload.user_active",
        "gateload.user_awake",
        "gateload.ops.AddUser.count"
    ]

    expvars_combined = ",".join(expvars)

    subprocess.call(["expvarmon",
                     "-ports={}".format(lgs_joined),
                     "-vars={}".format(expvars_combined)])
