
import requests
import json

# Server
# GET /
# POST db/_session
# DELETE db/_session


class SyncGateway:

    def __init__(self, ip, db_name):
        self.ip = "http://{}:4985".format(ip)
        self.db = Database(self.ip, db_name)

    def info(self):
        return requests.get(self.ip)

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

    def __init__(self, ip, name):
        self.ip = ip
        self.db_url = "{0}/{1}".format(self.ip, name)

    def info(self):
        return requests.get("{}".format(self.db_url, self.name))

    def all_docs(self):
        return requests.get("{}/_all_docs".format(self.db_url, self.name))

    def docs_from_keys(self, keys):
        return requests.post("{}/_all_docs".format(self.db_url), data={"keys": keys})

    def insert_docs(self, docs):
        return requests.post("{}/_bulk_docs".format(self.db_url), data={"docs": docs})

    def get_docs_bulk(self, attachments, revs):
        return requests.get(
            "/{}/_bulk_docs".format(self.db_url),
            data={
                "attachments": attachments,
                "revs": revs
            }
        )

    def changes(self):
        return requests.get("{}/_changes".format(self.db_url))

    def add_document(self, name, doc):
        headers = {"Content-Type": "application/json"}
        json_doc = json.dumps(doc)
        return requests.put("{0}/{1}".format(self.db_url, name), headers=headers, data=json_doc)



