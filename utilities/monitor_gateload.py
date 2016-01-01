import subprocess
import sys
from provisioning_config_parser import hosts_for_tag


if __name__ == "__main__":
    usage = """
    usage: python monitor_gateload.py"
    """

    # Get gateload ips from ansible inventory
    lgs_host_vars = hosts_for_tag("load_generators")
    lgs = [lg["ansible_ssh_host"] for lg in lgs_host_vars]

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
