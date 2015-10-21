import requests

import json

# Server
# GET /
# POST db/_session
# DELETE db/_session


class SyncGateway:

    def __init__(self, ip, db_name):
        self.public_port = 4984
        self.admin_port = 4985
        self.ip = "http://{}".format(ip)
        self.db = Database(self.ip, self.admin_port, self.public_port, db_name)

    def info(self):
        return requests.get("{0}:{1}".format(self.ip, self.public_port))

    #def stop(self):

    #def start(self):


# Database
# GET /{db}
# GET /{db}/_all_docs
# POST /{db}/_all_docs
# POST /{db}/_bulk_docs
# POST /{db}/_bulk_get
# GET /{db}/_changes

# Document
# POST /{db}


class Database:

    def __init__(self, ip, admin_port, public_port, name):
        self.ip = ip
        self.public_db_url = "{0}:{1}/{2}".format(self.ip, public_port, name)
        self.admin_db_url = "{0}:{1}/{2}".format(self.ip, admin_port, name)

    # admin endpoints
    def get_users(self):
        r = requests.get("{}/_user/".format(self.admin_db_url))
        assert r.status_code == 200
        return r.text

    def get_user(self, name):
        r = requests.get("{0}/_user/{1}".format(self.admin_db_url, name))
        assert r.status_code == 200
        return json.loads(r.text)

    def add_user(self, user):
        headers = {"Content-Type": "application/json"}
        json_doc = json.dumps({"name": user.name, "password": user.password, "admin_channels": user.channels})
        return requests.put("{0}/_user/{1}".format(self.admin_db_url, user.name), headers=headers, data=json_doc)

    # public endpoints
    def info(self):
        return requests.get("{}".format(self.public_db_url, self.name))

    def all_docs(self):
        return requests.get("{}/_all_docs".format(self.public_db_url, self.name))

    def docs_from_keys(self, keys):
        return requests.post("{}/_all_docs".format(self.public_db_url), data={"keys": keys})

    def insert_docs(self, docs):
        return requests.post("{}/_bulk_docs".format(self.public_db_url), data={"docs": docs})

    def get_docs_bulk(self, attachments, revs):
        return requests.get(
            "/{}/_bulk_docs".format(self.public_db_url),
            data={
                "attachments": attachments,
                "revs": revs
            }
        )

    def get_user_changes(self, user):
        headers = {
            "Authorization": "Basic {}".format(user.auth)
        }
        r = requests.get("{}/_changes".format(self.public_db_url), headers=headers)
        return json.loads(r.text)

    def add_document(self, name, doc):
        headers = {
            "Content-Type": "application/json"
        }
        json_doc = json.dumps(doc)
        return requests.put("{0}/{1}".format(self.public_db_url, name), headers=headers, data=json_doc)

    def add_user_document(self, doc_id, doc_body, user):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic {}".format(user.auth)
        }
        json_doc = json.dumps(doc_body)
        return requests.put("{0}/{1}".format(self.public_db_url, doc_id), headers=headers, data=json_doc, timeout=30)

    def add_user_bulk_documents(self, docs, user):

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic {}".format(user.auth)
        }

        docs_list = []
        for doc in docs:
            docs_list.append(doc.name_with_body())

        json_doc = json.dumps({"docs": docs_list})
        return requests.post("{0}/_bulk_docs".format(self.public_db_url), headers=headers, data=json_doc)
