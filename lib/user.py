import requests
import concurrent.futures
import json
import base64
import uuid
import re
import time

from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions
from collections import defaultdict
from scenarioprinter import ScenarioPrinter
from lib import settings
import logging
log = logging.getLogger(settings.LOGGER)


scenario_printer = ScenarioPrinter()


class User:
    def __init__(self, target, db, name, password, channels):

        self.name = name
        self.password = password
        self.db = db
        self.cache = {}
        self.changes_data = None
        self.channels = list(channels)
        self.target = target

        auth = base64.b64encode("{0}:{1}".format(self.name, self.password).encode())
        self._auth = auth.decode("UTF-8")
        self._headers = {'Content-Type': 'application/json', "Authorization": "Basic {}".format(self._auth)}

    def __str__(self):
        return "USER: name={0} password={1} db={2} channels={3} cache={4}".format(self.name, self.password, self.db, self.channels, len(self.cache))

    # GET /{db}/_all_docs
    def get_all_docs(self):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=Retry(total=settings.MAX_HTTP_RETRIES, backoff_factor=settings.BACKOFF_FACTOR, status_forcelist=settings.ERROR_CODE_LIST))
        session.mount("http://", adapter)

        resp = session.get("{0}/{1}/_all_docs".format(self.target.url, self.db), headers=self._headers)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()

        return resp.json()

    # PUT /{db}/{doc}
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
        log.info("{0} PUT {1}".format(self.name, doc_url))

        resp.raise_for_status()
        resp_json = resp.json()

        if resp.status_code == 201:
            self.cache[doc_id] = resp_json["rev"]

        return doc_id         

    # POST /{db}/_bulk_docs

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
        log.info("{0} POST {1}".format(self.name, resp.url))
        resp.raise_for_status()
        resp_json = resp.json()

        if len(resp_json) != len(doc_ids):
            raise Exception("Number of bulk docs inconsistent: resp_json['docs']:{} doc_ids:{}".format(len(resp_json), len(doc_ids)))

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
                        log.error('Generated an exception while adding doc_id : %s %s' % (doc, exc))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
                future = [executor.submit(self.add_bulk_docs, doc_names)]
                for f in concurrent.futures.as_completed(future):
                    try:
                        doc_list = f.result()
                        #print(doc_list)
                    except Exception as e:
                        log.error("Error adding bulk docs: {}".format(e))

        return True

    # GET /{db}/{doc}
    # PUT /{db}/{doc}
    def update_doc(self, doc_id, num_revision=1):

        updated_docs = dict()

        for i in range(num_revision):

            doc_url = self.target.url + '/' + self.db + '/' + doc_id
            resp = requests.get(doc_url, headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
            log.info("{0} GET {1}".format(self.name, resp.url))

            if resp.status_code == 200:
                data = resp.json()

                # Store number of updates on the document
                data['updates'] = int(data['updates']) + 1

                body = json.dumps(data)

                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(max_retries=Retry(total=settings.MAX_HTTP_RETRIES, backoff_factor=settings.BACKOFF_FACTOR, status_forcelist=settings.ERROR_CODE_LIST))
                session.mount("http://", adapter)

                put_resp = session.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)
                log.info("{0} PUT {1}".format(self.name, resp.url))

                if put_resp.status_code == 201:
                    data = put_resp.json()

                if "rev" not in data.keys():
                    log.error("Error: Did not find _rev property after Update response")
                    raise ValueError("Did not find _rev property after Update response")

                # Update revision number for stored doc id
                self.cache[doc_id] = data["rev"]

                # Store updated doc to return
                updated_docs[doc_id] = data["rev"]

                put_resp.raise_for_status()
            resp.raise_for_status()

        return updated_docs
                
    def update_docs(self, num_revs_per_doc=1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
            future_to_docs = {executor.submit(self.update_doc, doc_id, num_revs_per_doc): doc_id for doc_id in self.cache.keys()}
            
            for future in concurrent.futures.as_completed(future_to_docs):
                doc = future_to_docs[future]
                try:
                    doc_id = future.result()
                except Exception as exc:
                    log.error('Generated an exception while updating doc_id:%s %s' % (doc, exc))
                else:
                    log.info("Document: {} updated successfully".format(doc))

    def get_num_docs(self):
        return len(self.changes_data['results'])

    # returns a dictionary of type doc[revision]
    def get_num_revisions(self):
        docs = {}

        for obj in self.changes_data['results']:
            revision = obj["changes"][0]["rev"]
            log.debug(revision)
            match = re.search('(\d+)-\w+', revision)
            if match:
                log.debug("match found")
                revision_num = match.group(1)
                log.debug(revision_num)

            if obj["id"] in docs.keys():
                log.error("Key already exists")
                raise "Key already exists"
            else:
                docs[obj["id"]] = revision_num
        log.debug(docs)
        return docs

    # Check if the user created doc-ids are part of changes feed
    def check_doc_ids_in_changes_feed(self):
        superset = []
        errors = 0
        for obj in self.changes_data['results']:
            if obj["id"] in superset:
                log.error("doc id {} already exists".format(obj["id"]))
                raise KeyError("Doc id already exists")
            else:
                superset.append(obj["id"])

        for doc_id in self.cache.keys():
            if doc_id not in superset:
                log.error("doc-id {} missing from superset for User {}".format(doc_id, self.name))
                errors += 1
            else:
                log.info('Found doc-id {} for user {} in changes feed'.format(doc_id, self.name))
        return errors == 0

    # GET /{db}/_changes
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
        log.info("{0} GET {1}".format(self.name, r.url))
        r.raise_for_status()

        obj = json.loads(r.text)
        if len(obj["results"]) == 0:
            log.warn("Got no data in changes feed")
        self.changes_data = obj
        scenario_printer.print_changes_num(self.name, len(obj["results"]))
        return obj

    # GET /{db}/_changes?feed=longpoll
    def start_longpoll_changes_tracking(self, termination_doc_id, timeout=60000):

        previous_seq_num = "-1"
        current_seq_num = "0"
        request_timed_out = True

        docs = dict()
        continue_polling = True

        while continue_polling:
            # if the longpoll request times out or there have been changes, issue a new long poll request
            if request_timed_out or current_seq_num != previous_seq_num:

                previous_seq_num = current_seq_num

                params = {
                    "feed": "longpoll",
                    "include_docs": "true",
                    "timeout": timeout,
                    "since": current_seq_num
                }

                r = requests.get("{}/{}/_changes".format(self.target.url, self.db), headers=self._headers, params=params)
                log.info("{0} GET {1}".format(self.name, r.url))
                r.raise_for_status()
                obj = r.json()

                new_docs = obj["results"]

                # Check for duplicates in response doc_ids
                doc_ids = [doc["doc"]["_id"] for doc in new_docs if not doc["id"].startswith("_user/")]
                assert(len(doc_ids) == len(set(doc_ids)))

                if len(new_docs) == 0:
                    request_timed_out = True
                else:
                    for doc in new_docs:
                        # We are not interested in _user/ docs
                        if doc["id"].startswith("_user/"):
                            continue

                        # Stop polling if termination doc is recieved in _changes
                        if doc["id"] == termination_doc_id:
                            continue_polling = False
                            break

                        log.info("{} DOC FROM LONGPOLL _changes: {}: {}".format(self.name, doc["doc"]["_id"], doc["doc"]["_rev"]))
                        # Store doc
                        docs[doc["doc"]["_id"]] = doc["doc"]["_rev"]

                # Get latest sequence from changes request
                current_seq_num = obj["last_seq"]

                print(current_seq_num)

            time.sleep(0.1)

        return docs

    # GET /{db}/_changes?feed=continuous
    def start_continuous_changes_tracking(self, termination_doc_id):

        docs = dict()

        params = {
            "feed": "continuous",
            "include_docs": "true"
        }

        r = requests.get(url="{0}/{1}/_changes".format(self.target.url, self.db), headers=self._headers, params=params, stream=True)
        log.info("{0} GET {1}".format(self.name, r.url))

        # Wait for continuous changes
        for line in r.iter_lines():
            # filter out keep-alive new lines
            if line:
                doc = json.loads(line)

                # We are not interested in _user/ docs
                if doc["id"].startswith("_user/"):
                    continue

                # Close connection if termination doc is recieved in _changes
                if doc["doc"]["_id"] == termination_doc_id:
                    r.close()
                    return docs

                log.info("{} DOC FROM CONTINUOUS _changes: {}: {}".format(self.name, doc["doc"]["_id"], doc["doc"]["_rev"]))
                # Store doc
                # Should I be worried about duplicated in continuous _changes feed?
                docs[doc["doc"]["_id"]] = doc["doc"]["_rev"]
