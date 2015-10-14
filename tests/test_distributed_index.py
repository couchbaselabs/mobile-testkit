import sys

sys.path = ["..","lib"] + sys.path

# Local
# PUT /{db}/{local-doc-id}
# GET /{db}/{local-doc-id}
# DELETE /{db}/{local-doc-id}

from sync_gateway import SyncGateway

import random
import string
import uuid
import json


def test_1():

    sg_ips = ["172.23.105.204", "172.23.105.175"]
    # sg_ips = ["127.0.0.1"]

    sgs = []

    for sg_ip in sg_ips:
        sg = SyncGateway(sg_ip, "db")
        r = sg.info()
        print(r.status_code)
        assert r.status_code == 200
        sgs.append(sg)

    docs = []
    i = 0
    while i < 10000:
        key = "samplekey"
        value = '["123", "456"]'
        docs.append({key: value})
        i += 1

    sgs[0].db.add_user("seth", "pass123")
    sgs[1].db.add_user("ashvinder", "pass123")

    users_1 = sgs[0].db.get_users()
    print(users_1)

    users_2 = sgs[1].db.get_users()
    print(users_2)

    count = 0
    for doc in docs:
        doc_name = uuid.uuid4()
        sg_index = count % len(sgs)
        r = sgs[sg_index].db.add_document(doc_name, doc)
        print(r.status_code)
        print(count)
        count += 1


test_1()
