import subprocess
from provisioning_config_parser import hosts_for_tag


if __name__ == "__main__":
    usage = """
    usage: python monitor_gateload.py"
    """

    # Get gateload ips from ansible inventory
    lgs_host_vars = hosts_for_tag("load_generators")
    lgs = [lg["ansible_ssh_host"] for lg in lgs_host_vars]

    print("Monitoring sync_gateways: {}".format(lgs))
    lgs_with_port = [lg + ":9876" for lg in lgs]
    lgs_joined = ",".join(lgs_with_port)

    vars = "gateload.ops.PushToSubscriberInteractive.p95,gateload.ops.PushToSubscriberInteractive.p99,gateload.total_doc_pulled,gateload.total_doc_pushed,gateload.user_active,gateload.user_awake"

    subprocess.call(["expvarmon", "-ports={}".format(lgs_joined), "-vars={}".format(vars)])
