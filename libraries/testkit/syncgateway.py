import os
import requests
import json
import time
import libraries.testkit.settings
from libraries.testkit.debug import log_request
from libraries.testkit.debug import log_response
from libraries.testkit.admin import Admin
from libraries.provision.ansible_runner import AnsibleRunner
from requests import HTTPError
from keywords.SyncGateway import add_db_password_to_sg_config

import logging
log = logging.getLogger(libraries.testkit.settings.LOGGER)


class SyncGateway:

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]
        self.url = "http://{}:4984".format(target["ip"])
        self.hostname = target["name"]
        self._headers = {'Content-Type': 'application/json'}
        self.admin = Admin(self)
        self.cluster_config = cluster_config

        with open(self.cluster_config + ".json") as c:
            cluster = json.loads(c.read())

        self.cbs_ip = cluster["couchbase_servers"][0]["ip"]

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = self.ansible_runner.run_ansible_playbook(
            "stop-sync-gateway.yml",
            subset=self.hostname
        )
        return status

    def start(self, config):
        conf_path = os.path.abspath(config)
        add_db_password_to_sg_config(self.cluster_config, conf_path)

        log.info(">>> Starting sync_gateway with configuration: {}".format(conf_path))

        status = self.ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars={
                "sync_gateway_config_filepath": conf_path
            },
            subset=self.hostname
        )
        return status

    def restart(self, config):
        conf_path = os.path.abspath(config)
        add_db_password_to_sg_config(self.cluster_config, conf_path)
        log.info(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

        status = self.ansible_runner.run_ansible_playbook(
            "reset-sync-gateway.yml",
            extra_vars={
                "sync_gateway_config_filepath": conf_path,
            },
            subset=self.hostname
        )
        return status

    def verify_launched(self):
        r = requests.get(self.url)
        log.info("GET {} ".format(r.url))
        log.info("{}".format(r.text))
        r.raise_for_status()

    def create_db(self, name):
        return self.admin.create_db(name)

    def delete_db(self, name):
        return self.admin.delete_db(name)

    def reset(self):
        dbs = self.admin.get_dbs()
        for db in dbs:
            self.admin.delete_db(db)

    def start_push_replication(self,
                               target,
                               source_db,
                               target_db,
                               continuous=True,
                               use_remote_source=False,
                               channels=None,
                               async=False,
                               use_admin_url=False):

        if channels is None:
            channels = []

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "target": "{}/{}".format(target, target_db),
            "continuous": continuous
        }
        if use_remote_source:
            data["source"] = "{}/{}".format(sg_url, source_db)
        else:
            data["source"] = "{}".format(source_db)

        if len(channels) > 0:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = channels

        if async is True:
            data["async"] = True

        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_push_replication(self,
                              target,
                              source_db,
                              target_db,
                              continuous=True,
                              use_remote_source=False,
                              use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "target": "{}/{}".format(target, target_db),
            "cancel": True,
            "continuous": continuous
        }
        if use_remote_source:
            data["source"] = "{}/{}".format(sg_url, source_db)
        else:
            data["source"] = "{}".format(source_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def start_pull_replication(self,
                               source_url,
                               source_db,
                               target_db,
                               continuous=True,
                               use_remote_target=False,
                               use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "source": "{}/{}".format(source_url, source_db),
            "continuous": continuous
        }
        if use_remote_target:
            data["target"] = "{}/{}".format(sg_url, target_db)
        else:
            data["target"] = "{}".format(target_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_pull_replication(self,
                              source_url,
                              source_db,
                              target_db,
                              continuous=True,
                              use_remote_target=False,
                              use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "source": "{}/{}".format(source_url, source_db),
            "cancel": True,
            "continuous": continuous
        }
        if use_remote_target:
            data["target"] = "{}/{}".format(sg_url, target_db)
        else:
            data["target"] = "{}".format(target_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_replication_by_id(self, replication_id, use_admin_url=False):
        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "replication_id": "{}".format(replication_id),
            "cancel": True,
        }
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()

    def get_num_docs(self, db):
        r = requests.get("{}/{}/_all_docs".format(self.url, db))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["total_rows"]

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.hostname, self.ip)


def wait_until_doc_in_changes_feed(sg, db, doc_id):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        changes_results = sg.admin.get_global_changes(db)
        for changes_result in changes_results:
            if changes_result["id"] == doc_id:
                return

        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until doc {} showed up on changes feed, gave up".format(doc_id))


def wait_until_active_tasks_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        active_tasks = sg.admin.get_active_tasks()
        if len(active_tasks) == 0:
            return
        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until _active_tasks were empty, but they were never empty")


def wait_until_active_tasks_non_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        active_tasks = sg.admin.get_active_tasks()
        if len(active_tasks) > 0:
            return
        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until _active_tasks were non-empty, but they were never non-empty")


def wait_until_docs_sync(sg_user, doc_ids):
    for doc_id in doc_ids:
        wait_until_doc_sync(sg_user, doc_id)


def wait_until_doc_sync(sg_user, doc_id):
    max_tries_per_doc = 100
    sleep_retry_per_doc_seconds = 1

    for attempt in xrange(max_tries_per_doc):
        try:
            sg_user.get_doc(doc_id)
            # if we got a doc, and no exception was thrown, we're done
            return
        except HTTPError:
            time.sleep(sleep_retry_per_doc_seconds)

    raise Exception("Waited for doc {} to sync, but it never did".format(doc_id))


def assert_does_not_have_doc(sg_user, doc_id):
    # Make sure the doc did not propagate to the target
    got_exception = False
    try:
        sg_user.get_doc(doc_id)
    except HTTPError:
        got_exception = True
    assert got_exception is True


def assert_has_doc(sg_user, doc_id):
    doc = sg_user.get_doc(doc_id)
    assert doc is not None
    assert doc["_id"] == doc_id
