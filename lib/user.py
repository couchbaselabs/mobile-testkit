import requests
import concurrent.futures
import json
import base64
import uuid
import re

from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions
from collections import defaultdict
from scenarioprinter import ScenarioPrinter
from lib import settings

scenario_printer = ScenarioPrinter()


class User:
    def __init__(self, target, db, name, password, channels):

        self.name = name
        self.password = password
        self.db = db
        self.cache = {}
        self.channels = list(channels)
        self.target = target

        auth = base64.b64encode("{0}:{1}".format(self.name, self.password).encode())
        self._auth = auth.decode("UTF-8")
        self._headers = {'Content-Type': 'application/json', "Authorization": "Basic {}".format(self._auth)}

    def __str__(self):
        return "USER: name={0} password={1} db={2} channels={3} cache={4}".format(self.name, self.password, self.db, self.channels, len(self.cache))

    def add_doc(self, doc_id, content=None):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=Retry(total=settings.MAX_HTTP_RETRIES, backoff_factor=settings.BACKOFF_FACTOR, status_forcelist=settings.ERROR_CODE_LIST))
        session.mount("http://", adapter)

        doc_url = self.target.url + "/" + self.db + "/" + doc_id

        doc_body = dict()
        doc_body["updates"] = 0

        if self.channels:
            doc_body["channels"] = self.channels

        if content is not None:
            doc_body["content"] = content

        body = json.dumps(doc_body)

        resp = session.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)
        scenario_printer.print_status(resp)
        resp.raise_for_status()

        if resp.status_code == 201:
            self.cache[doc_id] = 0  # init doc revisions to 0

        return doc_id         

    def add_bulk_docs(self, doc_ids):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=Retry(total=settings.MAX_HTTP_RETRIES, backoff_factor=settings.BACKOFF_FACTOR, status_forcelist=settings.ERROR_CODE_LIST))
        session.mount("http://", adapter)

        # Create docs
        doc_list = []
        for doc_id in doc_ids:
            if self.channels:
                doc = {"_id": doc_id, "channels": self.channels, "updates": 0}
            else:
                doc = {"_id": doc_id, "updates": 0}
            doc_list.append(doc)

        docs = dict()
        docs["docs"] = doc_list
        data = json.dumps(docs)

        resp = session.post("{0}/{1}/_bulk_docs".format(self.target.url, self.db), headers=self._headers, data=data, timeout=settings.HTTP_REQ_TIMEOUT)
        scenario_printer.print_status(resp)
        resp.raise_for_status()
        resp_json = resp.json()

        if len(resp_json) != len(doc_ids):
            print("Number of bulk docs inconsistent: resp_json['docs']:{} doc_ids:{}".format(len(resp_json), len(doc_ids)))

        # Store docs from response in user's cache and save list of ids to return
        bulk_docs_ids = []
        if resp.status_code == 201:
            for doc in resp_json:
                self.cache[doc["id"]] = doc["rev"]
                bulk_docs_ids.append(doc["id"])

        # Return list of cache docs that were added
        return bulk_docs_ids

    def add_docs(self, num_docs, bulk=False, name_prefix=None):

        # If no name_prefix is specified, use uuids for doc_names
        if name_prefix is None:
            doc_names = [str(uuid.uuid4()) for _ in range(num_docs)]
        else:
            doc_names = [name_prefix + str(i) for i in range(num_docs)]

        if not bulk:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
                future_to_docs = {executor.submit(self.add_doc, doc): doc for doc in doc_names}
                for future in concurrent.futures.as_completed(future_to_docs):
                    doc = future_to_docs[future]
                    try:
                        doc_id = future.result()
                    except Exception as exc:
                        print('Generated an exception while adding doc_id : %s %s' % (doc, exc))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
                future = [executor.submit(self.add_bulk_docs, doc_names)]
                for f in concurrent.futures.as_completed(future):
                    try:
                        doc_list = f.result()
                        #print(doc_list)
                    except Exception as e:
                        print("Error adding bulk docs: {}".format(e))

        return True

    def update_doc(self, doc_id, num_revision=1):

        for i in range(num_revision):
            doc_url = self.target.url + '/' + self.db + '/' + doc_id
            resp = requests.get(doc_url, headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
    
            if resp.status_code == 200:
                data = resp.json()

                # Store number of updates on the document
                data['updates'] = int(data['updates']) + 1

                body = json.dumps(data)

                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(max_retries=Retry(total=settings.MAX_HTTP_RETRIES, backoff_factor=settings.BACKOFF_FACTOR, status_forcelist=settings.ERROR_CODE_LIST))
                session.mount("http://", adapter)

                put_resp = session.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)

                if put_resp.status_code == 201:

                    data = put_resp.json()
                    assert "rev" in data.keys()

                    # Update revision number for stored doc id
                    self.cache[doc_id]["rev"] = data["rev"]

                put_resp.raise_for_status()
            resp.raise_for_status()

        # Return doc_id, doc_rev kvp
        return self.cache[doc_id]
                
    def update_docs(self, num_revs_per_doc=1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
            future_to_docs = {executor.submit(self.update_doc, doc_id, num_revs_per_doc): doc_id for doc_id in self.cache.keys()}
            
            for future in concurrent.futures.as_completed(future_to_docs):
                doc = future_to_docs[future]
                try:
                    doc_id = future.result()
                except Exception as exc:
                    print('Generated an exception while updating doc_id:%s %s' % (doc, exc))
                else:
                    print "Document:", doc, "updated successfully"

    def get_changes(self, feed=None, limit=None, heartbeat=None, style=None,
                    since=None, include_docs=None, channels=None, filter=None):

        params = dict()

        if feed is not None:
            if feed != "normal" and feed != "continuous" and feed != "longpoll" and feed != "websocket":
                raise Exception("Invalid _changes feed type")
            params["feed"] = feed

        if limit is not None:
            params["limit"] = limit

        if heartbeat is not None:
            params["heartbeat"] = heartbeat

        if style is not None:
            params["style"] = style

        if since is not None:
            params["since"] = since

        if include_docs is not None:
            if include_docs:
                params["include_docs"] = "true"
            else:
                params["include_docs"] = "false"

        if channels is not None:
            params["channels"] = ",".join(channels)

        if filter is not None:
            if filter != "sync_gateway/bychannel":
                raise Exception("Invalid _changes filter type")
            params["filter"] = filter

        r = requests.get("{}/{}/_changes".format(self.target.url, self.db), headers=self._headers, params=params, timeout=settings.HTTP_REQ_TIMEOUT)
        r.raise_for_status()

        obj = json.loads(r.text)
        scenario_printer.print_changes_num(self.name, len(obj["results"]))
        return obj
