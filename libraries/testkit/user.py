import requests
import concurrent.futures
import json
import base64
import uuid
import re
import time

from requests.exceptions import HTTPError

from testkit.debug import log_request
from testkit.debug import log_response
from testkit import settings
import logging
log = logging.getLogger(settings.LOGGER)


class User:
    def __init__(self, target, db, name, password, channels):

        self.name = name
        self.password = password
        self.db = db
        self.cache = {}
        self.changes_data = None
        self.channels = list(channels)
        self.target = target

        self._headers = {'Content-Type': 'application/json'}

        if self.name is not None:
            auth = base64.b64encode("{0}:{1}".format(self.name, self.password).encode())
            self._auth = auth.decode("UTF-8")
            self._headers["Authorization"] = "Basic {}".format(self._auth)

    def __str__(self):
        return "USER: name={0} password={1} db={2} channels={3} cache={4}".format(self.name, self.password, self.db, self.channels, len(self.cache))

    # GET /{db}/{doc}
    # GET /{db}/{local-doc-id}
    def get_doc(self, doc_id):
        resp = requests.get("{0}/{1}/{2}".format(self.target.url, self.db, doc_id), headers=self._headers)
        log.debug("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # POST /{db}/bulk_get
    def get_docs(self, doc_ids):
        docs_array = [{"id": doc_id} for doc_id in doc_ids]
        body = {"docs": docs_array}

        resp = requests.post("{0}/{1}/_bulk_get".format(self.target.url, self.db), headers=self._headers, data=json.dumps(body))
        log.debug("POST {}".format(resp.url))
        resp.raise_for_status()

        # Parse Mime and build python obj of docs returned
        # May need to fix this if we start including attachments
        docs = []
        for part in resp.text.splitlines():
            if part.startswith("{"):
                docs.append(json.loads(part))

        return docs

    # GET /{db}/_all_docs
    def get_all_docs(self):
        resp = requests.get("{0}/{1}/_all_docs".format(
            self.target.url,
            self.db,
        ), headers=self._headers)
        log.debug("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # DELETE /{db}/{doc-id}
    def delete_doc(self, doc_id, doc_rev=None):

        if doc_rev is None:
            # fetch latest revision of doc
            doc_to_del = self.get_doc(doc_id)
            rev_to_delete = doc_to_del["_rev"]
        else:
            # use specific rev
            rev_to_delete = doc_rev

        # delete that revision
        resp = requests.delete("{0}/{1}/{2}?rev={3}".format(
            self.target.url,
            self.db,
            doc_id,
            rev_to_delete,
        ), headers=self._headers)

        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/{doc}
    # PUT /{db}/{local-doc-id}
    def add_doc(self, doc_id=None, content=None, retries=False):

        doc_body = dict()
        doc_body["updates"] = 0

        if self.channels:
            doc_body["channels"] = self.channels

        if content is not None:
            doc_body["content"] = content

        body = json.dumps(doc_body)

        if doc_id is None:
            # Use a POST and let sync_gateway generate an id
            resp = requests.post("{0}/{1}/".format(self.target.url, self.db), headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)
            log.debug("{0} POST {1}".format(self.name, resp.url))
        else:
            # If the doc id is specified, use PUT with doc_id in url
            doc_url = self.target.url + "/" + self.db + "/" + doc_id

            if retries:
                # This was using invalid construction of HTTP adapter and currently is not used anywhere.
                # Retry behavior will be the same as regular behavior. This is a legacy API so just adding this
                # to do execute the same behavior whether or not retries is specifiec
                resp = requests.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)
            else:
                resp = requests.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)

            log.debug("{0} PUT {1}".format(self.name, resp.url))

        resp.raise_for_status()
        resp_json = resp.json()

        # 200 as result of POST to /{db}/, 201 is result of PUT to /{db}/{doc}
        if resp.status_code == 200 or resp.status_code == 201:
            if doc_id is None:
                # Get id generated from sync_gateway in response
                doc_id = resp_json["id"]
                self.cache[doc_id] = resp_json["rev"]
            elif doc_id is not None and not doc_id.startswith("_local/"):
                # Do not store local docs in user cache because they will not show up in the _changes feed
                self.cache[doc_id] = resp_json["rev"]

        return doc_id

    # POST /{db}/_bulk_docs
    def add_bulk_docs(self, doc_ids, retries=False):

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

        if retries:
            # This was using invalid construction of HTTP adapter and currently is not used anywhere.
            # Retry behavior will be the same as regular behavior. This is a legacy API so just adding this
            # to do execute the same behavior whether or not retries is specifiec
            resp = requests.post("{0}/{1}/_bulk_docs".format(self.target.url, self.db), headers=self._headers, data=data, timeout=settings.HTTP_REQ_TIMEOUT)
        else:
            resp = requests.post("{0}/{1}/_bulk_docs".format(self.target.url, self.db), headers=self._headers, data=data, timeout=settings.HTTP_REQ_TIMEOUT)

        log.debug("{0} POST {1}".format(self.name, resp.url))
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

    def add_docs(self, num_docs, bulk=False, name_prefix=None, retries=False):

        errors = list()

        # If no name_prefix is specified, use uuids for doc_names
        if name_prefix is None:
            doc_names = [str(uuid.uuid4()) for _ in range(num_docs)]
        else:
            doc_names = [name_prefix + str(i) for i in range(num_docs)]

        if not bulk:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:

                if retries:
                    future_to_docs = {executor.submit(self.add_doc, doc, content=None, retries=True): doc for doc in doc_names}
                else:
                    future_to_docs = {executor.submit(self.add_doc, doc, content=None): doc for doc in doc_names}

                for future in concurrent.futures.as_completed(future_to_docs):
                    doc = future_to_docs[future]
                    log.debug(doc)
                    try:
                        doc_id = future.result()
                        log.debug(doc_id)
                    except HTTPError as e:
                        log.info("HTTPError: {0} {1} {2}".format(self.name, e.response.url, e.response.status_code))
                        errors.append((e.response.url, e.response.status_code))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:

                if retries:
                    future = [executor.submit(self.add_bulk_docs, doc_names, retries=True)]
                else:
                    future = [executor.submit(self.add_bulk_docs, doc_names)]

                for f in concurrent.futures.as_completed(future):
                    try:
                        doc_list = f.result()
                        log.debug(doc_list)
                    except HTTPError as e:
                        log.info("HTTPError: {0} {1} {2}".format(self.name, e.response.url, e.response.status_code))
                        errors.append((e.response.url, e.response.status_code))

        return errors

    def add_design_doc(self, doc_id, content):
        data = json.dumps(content)
        r = requests.put("{0}/{1}/_design/{2}".format(self.target.url, self.db, doc_id), headers=self._headers, data=data)
        log_request(r)
        log_response(r)
        r.raise_for_status()

    # GET /{db}/{doc}
    # PUT /{db}/{doc}
    def update_doc(self, doc_id, num_revision=1, content=None, retries=False):

        updated_docs = dict()

        for i in range(num_revision):

            doc_url = self.target.url + '/' + self.db + '/' + doc_id
            resp = requests.get(doc_url, headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
            log.debug("{0} GET {1}".format(self.name, resp.url))

            if resp.status_code == 200:
                data = resp.json()

                # Store number of updates on the document
                data['updates'] = int(data['updates']) + 1

                if content is not None:
                    data['content'] = content

                body = json.dumps(data)

                if retries:
                    # This was using invalid construction of HTTP adapter and currently is not used anywhere.
                    # Retry behavior will be the same as regular behavior. This is a legacy API so just adding this
                    # to do execute the same behavior whether or not retries is specifiec
                    put_resp = requests.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)
                else:
                    put_resp = requests.put(doc_url, headers=self._headers, data=body, timeout=settings.HTTP_REQ_TIMEOUT)

                log.debug("{0} PUT {1}".format(self.name, resp.url))

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

    def update_docs(self, num_revs_per_doc=1, retries=False):

        errors = list()

        if len(self.cache.keys()) == 0:
            log.warning("Unable to find any docs to update")

        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:

            if retries:
                future_to_docs = {executor.submit(self.update_doc, doc_id, num_revs_per_doc, retries=True): doc_id for doc_id in self.cache.keys()}
            else:
                future_to_docs = {executor.submit(self.update_doc, doc_id, num_revs_per_doc): doc_id for doc_id in self.cache.keys()}

            for future in concurrent.futures.as_completed(future_to_docs):
                doc = future_to_docs[future]
                try:
                    doc_id = future.result()
                    logging.debug(doc_id)
                except HTTPError as e:
                    log.error("{0} {1} {2}".format(self.name, e.response.url, e.response.status_code))
                    errors.append((e.response.url, e.response.status_code))
                else:
                    log.debug("Document: {} updated successfully".format(doc))

        return errors

    def get_num_docs(self):
        # add this variable to not count "_user" id in changes feed
        adjustment = 0
        for index in range(len(self.changes_data['results'])):
            if self.changes_data['results'][index]['id'].startswith("_user"):
                adjustment += 1
                log.info("Found \"_user\" id in changes feed")
                log.info(self.changes_data['results'][index]['id'])
        log.info("get_num_docs = {}".format(len(self.changes_data['results']) - adjustment))
        return len(self.changes_data['results']) - adjustment

    # returns a dictionary of type doc[revision]
    def get_num_revisions(self):
        docs = {}

        for obj in self.changes_data['results']:
            if obj["id"].startswith("_user"):
                continue
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
                log.debug('Found doc-id {} for user {} in changes feed'.format(doc_id, self.name))
        return errors == 0

    # POST /{db}/_changes
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
                params["include_docs"] = True
            else:
                params["include_docs"] = False

        if channels is not None:
            params["channels"] = ",".join(channels)

        if filter is not None:
            if filter != "sync_gateway/bychannel":
                raise Exception("Invalid _changes filter type")
            params["filter"] = filter

        data = json.dumps(params)

        r = requests.post("{}/{}/_changes".format(self.target.url, self.db), headers=self._headers, data=data, timeout=settings.HTTP_REQ_TIMEOUT)
        log.debug("{0} POST {1}".format(self.name, r.url))
        r.raise_for_status()

        obj = json.loads(r.text)
        if len(obj["results"]) == 0:
            log.warn("Got no data in changes feed")
        self.changes_data = obj
        log.debug("{0}:{1}".format(self.name, len(obj["results"])))
        return obj

    # POST /{db}/_changes?feed=longpoll
    def start_longpoll_changes_tracking(self, termination_doc_id=None, timeout=10000, loop=True):

        previous_seq_num = "-1"
        current_seq_num = "0"
        request_timed_out = True

        docs = dict()
        continue_polling = True

        while continue_polling:
            # if the longpoll request times out or there have been changes, issue a new long poll request
            if request_timed_out or current_seq_num != previous_seq_num:

                previous_seq_num = current_seq_num

                # Android client POST data
                # {"limit":50,"feed":"longpoll","since":15,"style":"all_docs","heartbeat":300000}
                # Make sure to use similar parameters in POST
                params = {
                    "feed": "longpoll",
                    "include_docs": True,
                    "style": "all_docs",
                    "heartbeat": 300000,
                    "timeout": timeout,
                    "since": current_seq_num
                }

                data = json.dumps(params)

                r = requests.post("{}/{}/_changes".format(self.target.url, self.db), headers=self._headers, data=data)
                log.debug("{0} {1} {2}\n{3}\n{4}".format(
                    self.name,
                    r.request.method,
                    r.request.url,
                    r.request.headers,
                    r.request.body))

                # If call is unsuccessful (ex. db goes offline), return docs
                if r.status_code != 200:
                    # HACK: return last sequence number and docs to allow closed connections
                    raise HTTPError({"docs": docs, "last_seq_num": current_seq_num})

                obj = r.json()

                new_docs = obj["results"]
                log.debug("CHANGES RESULT: {}".format(obj))

                # Check for duplicates in response doc_ids
                doc_ids = [doc["doc"]["_id"] for doc in new_docs if not doc["id"].startswith("_user/")]
                if len(doc_ids) != len(set(doc_ids)):
                    for item in set(doc_ids):
                        if doc_ids.count(item) > 1:
                            log.error("DUPLICATE!!!: {}".format(item))

                # HACK - need to figure out a better way to check this
                if len(new_docs) == 0:
                    request_timed_out = True
                else:
                    for doc in new_docs:

                        # We are not interested in _user/ docs
                        if doc["id"].startswith("_user/"):
                            continue

                        log.debug("{} DOC FROM LONGPOLL _changes: {}: {}".format(self.name, doc["doc"]["_id"], doc["doc"]["_rev"]))

                        # Stop polling if termination doc is recieved in _changes
                        if termination_doc_id is not None and doc["id"] == termination_doc_id:
                            log.debug("Termination doc found")
                            continue_polling = False
                            break

                        # Store doc
                        docs[doc["doc"]["_id"]] = doc["doc"]["_rev"]

                # Get latest sequence from changes request
                current_seq_num = obj["last_seq"]

                log.debug("SEQ_NUM {}".format(current_seq_num))

                if loop is False:
                    if len(new_docs) == 1:
                        # Hack around the fact that the first call to
                        # _changes may return an _user docs which will not be stored
                        continue

                    # Exit after one longpoll request that returns docs
                    break

            time.sleep(0.1)

        return docs, current_seq_num

    # POST /{db}/_changes?feed=continuous
    def start_continuous_changes_tracking(self, termination_doc_id=None):

        docs = dict()

        params = {
            "feed": "continuous",
            "include_docs": True
        }

        data = json.dumps(params)

        r = requests.post(url="{0}/{1}/_changes".format(self.target.url, self.db), headers=self._headers, data=data, stream=True)
        log.debug("{0} POST {1}".format(self.name, r.url))

        # Wait for continuous changes
        for line in r.iter_lines():
            # filter out keep-alive new lines
            if line:
                doc = json.loads(line)

                # We are not interested in _user/ docs
                if doc["id"].startswith("_user/"):
                    continue

                # Close connection if termination doc is recieved in _changes
                if termination_doc_id is not None and doc["doc"]["_id"] == termination_doc_id:
                    r.close()
                    return docs

                log.debug("{} DOC FROM CONTINUOUS _changes: {}: {}".format(self.name, doc["doc"]["_id"], doc["doc"]["_rev"]))
                # Store doc
                docs[doc["doc"]["_id"]] = doc["doc"]["_rev"]

        # if connection is closed from server
        return docs
