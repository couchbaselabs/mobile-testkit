from keywords import utils
import subprocess


def test_add_cbs_to_sg_config_server_field():
    subprocess.call("echo '{\"couchbase_servers\": [\n{\n\"ip\": \"192.168.33.10\",\n \"name\": \"cb1\"\n},\n {\n\"ip\": \"192.168.33.11\",\n\"name\": \"cb2\"\n},\n{\n\"ip\": \"192.168.33.12\",\n\"name\": \"cb3\"\n}\n]}' > resources/cluster_configs/test.json", shell=True)
    cluster_config = "resources/cluster_configs/test"
    expected_string = "192.168.33.10,192.168.33.11,192.168.33.12"
    assert expected_string == utils.add_cbs_to_sg_config_server_field(cluster_config)
    subprocess.call("rm resources/cluster_configs/test.json", shell=True)
