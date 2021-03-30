from keywords.remoteexecutor import RemoteExecutor
from utilities.cluster_config_utils import load_cluster_config_json
import subprocess


def create_files_with_content(content, sg_platform, node_ip, file_name, cluster_conf, path=None):
    if path is None:
        if sg_platform == "windows":
            path = "C:\\\\tmp\\\\{}".format(file_name)
        else:
            path = "/tmp/{}".format(file_name)

    if sg_platform == "windows":
        json_cluster = load_cluster_config_json(cluster_conf)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(node_ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(node_ip)

    create_command = "echo {} > {}".format(content, path)
    if sg_platform == "macos":
        subprocess.check_output(create_command, shell=True)
    else:
        remote_executor.execute(create_command)
    return path
