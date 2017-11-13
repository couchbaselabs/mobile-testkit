from requests import Session
from keywords.utils import log_info


class CBLRestClient:

    def __init__(self):
        headers = {"Content-Type": "application/json"}
        self._session = Session()
        self._session.headers = headers

    def database_create(self, url, name):
        url = "{}/database_create?name=\"{}\"".format(url, name)
        resp = self._session.post(url)
        log_info(url)
        resp.raise_for_status()
        return resp.content

    def database_getName(self, url, db):
        url = "{}/database_getName?database={}".format(url, db)
        log_info(url)
        resp = self._session.post(url)
        resp.raise_for_status()
        return resp.content

    def release(self, url, database):
        resp = self._session.post("{}/release?object=\"{}\"".format(url, database))
        resp.raise_for_status()
        return resp

    def document_create_with_dict(self, url, doc_id, doc):
        url = "{}/document_create?id=\"{}\"&dictionary=\"{}\"".format(url, doc_id, doc)
        resp = self._session.post(url)
        log_info(url)
        resp.raise_for_status()
        return resp.content

    def document_create(self, url, doc_id):
        url = "{}/document_create?id=\"{}\"".format(url, doc_id)
        resp = self._session.post(url)
        log_info(url)
        resp.raise_for_status()
        return resp.content
