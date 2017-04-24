import json
import base64

from couchbase.bucket import Bucket
from libraries.provision.ansible_runner import AnsibleRunner


class Server:

    """
    Old code -- slowly being deprecated

    Use keywords/couchbaseserver.py for future development
    """

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]

        with open("{}.json".format(cluster_config)) as f:
            cluster = json.loads(f.read())

        server_port = 8091
        server_scheme = "http"

        if cluster["cbs_ssl_enabled"]:
            server_port = 18091
            server_scheme = "https"

        self.url = "{}://{}:{}".format(server_scheme, target["ip"], server_port)
        self.hostname = target["name"]

        auth = base64.b64encode("{0}:{1}".format("Administrator", "password").encode())
        auth = auth.decode("UTF-8")
        self._headers = {'Content-Type': 'application/json', "Authorization": "Basic {}".format(auth)}

    def get_bucket(self, bucket_name):
        connection_str = "couchbase://{}/{}".format(self.ip, bucket_name)
        return Bucket(connection_str, password='password')

    def __repr__(self):
        return "Server: {}:{}\n".format(self.hostname, self.ip)
