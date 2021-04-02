import os
from keywords.constants import ENVIRONMENT_FILE
from libraries.provision.ansible_runner import AnsibleRunner


def create_files_with_content(content, sg_platform, sg_hostname, file_name, cluster_conf, path=None):
    ansible_runner = AnsibleRunner(cluster_conf)
    if path is None:
        path = "/tmp/" + file_name
        if sg_platform == "windows":
            path = "C:\\\\tmp\\\\" + file_name

    environment_file = os.path.abspath(ENVIRONMENT_FILE)
    environmentFileWriter = open(environment_file, "w")
    environmentFileWriter.write(content)
    environmentFileWriter.close()
    playbook_vars = {
        "file_to_copy": environment_file,
        "destination_file": path
    }
    ansible_runner.run_ansible_playbook(
        "copy_files_to_nodes.yml",
        extra_vars=playbook_vars,
        subset=sg_hostname
    )
    return path
