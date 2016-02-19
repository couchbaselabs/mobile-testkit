import subprocess
import requests
import os

from couchdb import Server

from lib import settings
import logging
log = logging.getLogger(settings.LOGGER)

class LiteServ:
    def __init__(self, port):
        ip = "192.168.0.19"
        self.url = "http://{}:{}".format(ip, port)
        self.server = Server(url=self.url)
        subprocess.call(["monkeyrunner", "utilities/cbl_android_tool.py", "--port={}".format(port)])

    def verify_lauched(self):
        r = requests.get(self.url)
        log.info("GET {} ".format(r.url))
        r.raise_for_status()
        return r.text

    def create_db(self, name):
        self.server.create(name)

    def delete_db(self, name):
        self.server.delete(name)


#status = subprocess.call('adb forward tcp:$* tcp:$*')
#assert(status == 0)

# from subprocess import call
# import time
# import requests
# import json
#
# sg_url = "http://172.23.105.163:4984/db"
# ls_urls = []
# local_db = "local_db"
#
# def launch_lite_serv(port):
#     call([" nohup ./LiteServ --dir /tmp/liteserv/" + port + " --port " + port + "&"],shell=True)
#
# def kill_lite_serv():
#     call(["killall LiteServ"],shell=True)
#     call(["rm -rf /tmp/liteserv/"],shell=True)
#
# def create_local_db(url,db_name):
#     db_url = url + "/" + db_name
#     headers = {'Content-Type': 'application/json'}
#     r = requests.put(db_url,headers=headers,data={})
#     print r.json()
#
# def setup_pull_replication(lite_user,sg_url):
#     target = lite_user + "/_replicate"
#     headers = {'Content-Type': 'application/json'}
#     payload = {"source": sg_url, "target": "local_db","continuous":True}
#     doc = json.dumps(payload)
#     #print target,doc
#     r = requests.post(target,headers=headers,data=doc)
#     print r.json()
#
# def create_sg_docs(sg_url):
#     target = sg_url + "/mydoc"
#     headers = {'Content-Type': 'application/json'}
#     payload = {'userID': 'userA','mykey':'myvalue', 'count': 0}
#     doc = json.dumps(payload)
#     r = requests.put(target,headers=headers,data=doc)
#     print r.json()
#
# def main(num_users):
#     port = 49840
#
#     kill_lite_serv()
#
#     # launch lite servs
#     for user in range(num_users):
#         launch_lite_serv(str(port))
#         ls_url = "http://localhost:" + str(port)
#         ls_urls.append(ls_url)
#         port = port + 2
#
#     time.sleep(1)
#
#     # create db
#     for lite_user in ls_urls:
#         create_local_db(lite_user,local_db)
#
#     # setup pull replication
#     for lite_user in ls_urls:
#         setup_pull_replication(lite_user,sg_url)
#
#     # create sg docs
#     create_sg_docs(sg_url)
#
#     time.sleep(5)
#     #kill_lite_serv()
#
# num_users = 10
# main(num_users)