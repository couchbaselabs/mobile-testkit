import requests
import concurrent.futures
import json
import pprint
import copy_reg
import types
import time
import base64
import uuid
import re
from collections import defaultdict


class User:
    def __init__(self, target, db, name, password, channels):

        self.name = name
        self.password = password
        self.db = db
        self.docs_info = {}
        self.channels = list(channels)
        self.target = target

        auth = base64.b64encode("{0}:{1}".format(self.name, self.password).encode())
        self._auth = auth.decode("UTF-8")
        self._headers = {'Content-Type': 'application/json', "Authorization": "Basic {}".format(self._auth)}

    def __str__(self):
        return "USER: name={0} password={1} db={2} channels={3}".format(self.name, self.password, self.db, self.channels)


    def add_doc(self, doc_id):
        doc_url = self.target.url + "/" + self.db + "/" + doc_id
        doc_body = {}
        doc_body["updates"] = 0
        if self.channels:
            doc_body["channels"] = self.channels
        body = json.dumps(doc_body)
        resp = requests.put(doc_url, headers=self._headers, data=body)
        if resp.status_code == 201:
            self.docs_info[doc_id] = 0  # init doc revisions to 0
        resp.raise_for_status()
        return doc_id         

    def add_docs(self, num_docs, uuid_names=False):

        if uuid_names:
            doc_names = [str(uuid.uuid4()) for _ in range(num_docs)]
        else:
            doc_names = ["test-" + str(i) for i in range(num_docs)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_docs = {executor.submit(self.add_doc, doc): doc for doc in doc_names}
            for future in concurrent.futures.as_completed(future_to_docs):
                doc = future_to_docs[future]
                try:
                    doc_id = future.result()
                    print(doc_id)
                except Exception as exc:
                    print('Generated an exception while adding doc_id : %s %s' % (doc, exc))
                else:
                    print "Document:", doc, "added successfully"
        return True

    def update_doc(self, doc_id, num_revision=1):

        for i in range(num_revision):
            doc_url = self.target.url + '/' + self.db + '/' + doc_id
            resp = requests.get(doc_url, headers=self._headers)
    
            if resp.status_code == 200:
                data = resp.json()
                data['updates'] = int(data['updates']) + 1
                
                body = json.dumps(data)
                put_resp = requests.put(doc_url, headers=self._headers, data=body)
                if put_resp.status_code == 201:
                    data = put_resp.json()
                    if data["rev"]:
                        self.docs_info[doc_id] = data["rev"]  # init doc revisions to 0
                    else:
                        print "Error: Did not fine _rev after Update response"
                put_resp.raise_for_status()
            resp.raise_for_status()
                
    def update_docs(self, num_revs_per_doc=1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_docs = {executor.submit(self.update_doc, doc_id, num_revs_per_doc): doc_id for doc_id in self.docs_info.keys()}
            
            for future in concurrent.futures.as_completed(future_to_docs):
                doc = future_to_docs[future]
                try:
                    doc_id = future.result()
                except Exception as exc:
                    print('Generated an exception while updating doc_id:%s %s' % (doc, exc))
                else:
                    print "Document:", doc, "updated successfully"

    def get_num_docs(self, doc_name_pattern):
        data = self.get_changes()
        p = re.compile(doc_name_pattern)
        docs = []
        for obj in data['results']:
            m = p.match(obj['id'])
            if m:
                docs.append(obj['id'])
        return len(docs)

    def get_changes(self, with_docs=False):
        if with_docs:
            r = requests.get("{}/{}/_changes?include_docs=true".format(self.target.url, self.db), headers=self._headers)
        else:
            r = requests.get("{}/{}/_changes".format(self.target.url, self.db), headers=self._headers)
        return json.loads(r.text)

    def verify_all_docs_from_changes_feed(self, num_revision, doc_name_pattern):
        status_num_docs = status_revisions = status_content = True
        p = re.compile(doc_name_pattern)
        data = self.get_changes(with_docs=True)
        docs = defaultdict(list)

        for obj in data['results']:
            m = p.match(obj['id'])
            if m:
                docs[obj['id']].append(obj['doc']['_rev'])
                docs[obj['id']].append(obj['doc']['updates'])
        
        print "Num doc created", len(self.docs_info.keys())
        print "Num docs found", len(docs.keys())
        
        if len(self.docs_info.keys()) == len(docs.keys()):
            print "Success, found expected num docs"
        else:
            print "Error: Num docs did not match"
            status_num_docs = False

        for doc_id in docs.keys():
            if doc_id in self.docs_info.keys():
                if docs[doc_id][0] == self.docs_info[doc_id]:
                    print "Revision matched for doc_id", doc_id
                else:
                    print "Error, Revision did not match", doc_id
                    status_revisions = False

                if num_revision:
                    if docs[doc_id][1] == num_revision:
                        print "Num updates matches with", num_revision
                    else:
                        print "Error: expected update count did not match", num_revision
                        status_content = False

        status = status_num_docs & status_revisions & status_content
        return status