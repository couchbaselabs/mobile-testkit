import time
import os

from CBLClient.Client import Client
from CBLClient.Args import Args
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info, is_replicator_in_connection_retry
from utilities.cluster_config_utils import sg_ssl_enabled


class Replication(object):
    '''
    classdocs
    '''

    def __init__(self, base_url):
        '''
        Constructor
        '''
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")
        self._client = Client(base_url)
        self.config = None

    def configure(self, source_db, target_url=None, target_db=None,
                  replication_type="push_pull", continuous=False,
                  push_filter=False, pull_filter=False, channels=None,
                  documentIDs=None, replicator_authenticator=None,
                  headers=None, filter_callback_func='', conflict_resolver='',
                  heartbeat=None, max_retries=None, max_retry_wait_time=None,
                  auto_purge=None, encryptor=None):
        args = Args()
        args.setMemoryPointer("source_db", source_db)
        args.setBoolean("continuous", continuous)
        args.setBoolean("push_filter", push_filter)
        args.setBoolean("pull_filter", pull_filter)
        args.setString("filter_callback_func", filter_callback_func)
        args.setString("conflict_resolver", conflict_resolver)

        if max_retries is not None:
            args.setString("max_retries", max_retries)

        if max_retry_wait_time is not None:
            args.setString("max_timeout", max_retry_wait_time)

        if heartbeat is not None:
            args.setString("heartbeat", heartbeat)

        if channels is not None:
            args.setArray("channels", channels)

        if documentIDs is not None:
            args.setArray("documentIDs", documentIDs)

        if replicator_authenticator is not None:
            args.setMemoryPointer("authenticator", replicator_authenticator)

        if replication_type is not None:
            args.setString("replication_type", replication_type)

        if headers is not None:
            args.setDictionary("headers", headers)

        if target_url is not None:
            args.setString("target_url", target_url)

        if target_db is not None:
            args.setMemoryPointer("target_db", target_db)

        if auto_purge is not None:
            args.setString("auto_purge", auto_purge)

        cluster_config = os.environ["CLUSTER_CONFIG"]
        if sg_ssl_enabled(cluster_config):
            args.setString("pinnedservercert", "sg_cert")

        if encryptor is not None:
            args.setMemoryPointer("encryptor", encryptor)

        return self._client.invokeMethod("replicatorConfiguration_configure", args)

    """def create(self, source_db, target_db=None, target_url=None):
        args = Args()
        args.setMemoryPointer("sourceDb", source_db)
        if target_db:
            args.setMemoryPointer("targetDb", target_db)
        elif target_url:
            args.setMemoryPointer("targetURI", target_url)
        else:
            raise Exception("Pass either target_db or target_url.")
        return self._client.invokeMethod("replicatorConfiguration_create",
                                         args) """

    def getAuthenticator(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getAuthenticator",
                                         args)

    def getChannels(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getChannels",
                                         args)

    def getConflictResolver(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getConflictResolver",
                                         args)

    def getDatabase(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getDatabase",
                                         args)

    def getDocumentIDs(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getDocumentIDs",
                                         args)

    def getPinnedServerCertificate(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getPinnedServerCertificate",
                                         args)

    def getReplicatorType(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getReplicatorType",
                                         args)

    def getTarget(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getTarget", args)

    def isContinuous(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_isContinuous",
                                         args)

    def setAuthenticator(self, configuration, authenticator):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("replicatorConfiguration_setAuthenticator",
                                         args)

    def setChannels(self, configuration, channels):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("channels", channels)
        return self._client.invokeMethod("replicatorConfiguration_setChannels",
                                         args)

    def setConflictResolver(self, configuration, conflict_resolver):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("conflictResolver", conflict_resolver)
        return self._client.invokeMethod("replicatorConfiguration_setConflictResolver",
                                         args)

    def setContinuous(self, configuration, continuous):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setBoolean("continuous", continuous)
        return self._client.invokeMethod("replicatorConfiguration_setContinuous",
                                         args)

    def setDocumentIDs(self, configuration, document_ids):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("documentIds", document_ids)
        return self._client.invokeMethod("replicatorConfiguration_setDocumentIDs",
                                         args)

    def setPinnedServerCertificate(self, configuration, cert):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("cert", cert)
        return self._client.invokeMethod("replicatorConfiguration_setPinnedServerCertificate",
                                         args)

    def setReplicatorType(self, configuration, repl_type):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("replType", repl_type)
        return self._client.invokeMethod("replicatorConfiguration_setReplicatorType",
                                         args)

    def setAutoPurgeFlag(self, configuration, auto_purge_flag=True):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setBoolean("auto_purge", auto_purge_flag)
        return self._client.invokeMethod("replicatorConfiguration_setAutoPurge", args)

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("replicator_create", args)

    def getConfig(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_config", args)

    def addReplicatorEventChangeListener(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_addReplicatorEventChangeListener", args)

    def removeReplicatorEventListener(self, replicator, change_listener):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_removeReplicatorEventListener", args)

    def getReplicatorEventChanges(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_replicatorEventGetChanges", args)

    def getReplicatorEventChangesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_replicatorEventChangesCount", args)

    def addChangeListener(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_addChangeListener", args)

    def removeChangeListener(self, replicator, change_listener):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_removeChangeListener", args)

    def toString(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_toString", args)

    def start(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_start", args)

    def stop(self, replicator, max_times=15):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        # return self._client.invokeMethod("replicator_stop", args)
        self._client.invokeMethod("replicator_stop", args)
        count = 0
        while self.getActivitylevel(replicator) != "stopped" and count < max_times:
            time.sleep(2)
            count += 1
        if self.getActivitylevel(replicator) != "stopped":
            raise Exception("Failed to stop the replicator: {}".format(self.getActivitylevel(replicator)))

    def status(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_status", args)

    def getCompleted(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getCompleted", args)

    def getTotal(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getTotal", args)

    def getActivitylevel(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getActivityLevel", args)

    def getError(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getError", args)

    def getChangesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_changeListenerChangesCount", args)

    def getChangesChangeListener(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_changeListenerGetChanges", args)

    def configure_and_replicate(self, source_db, replicator_authenticator=None, target_db=None, target_url=None, replication_type="push_pull", continuous=True,
                                channels=None, err_check=True, wait_until_idle=True, heartbeat=None, auto_purge=None):
        if target_db is None:
            repl_config = self.configure(source_db, target_url=target_url, continuous=continuous,
                                         replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator, heartbeat=heartbeat, auto_purge=auto_purge)
        else:
            repl_config = self.configure(source_db, target_db=target_db, continuous=continuous,
                                         replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator, heartbeat=heartbeat, auto_purge=auto_purge)
        repl = self.create(repl_config)
        self.start(repl)
        if wait_until_idle:
            self.wait_until_replicator_idle(repl, err_check)
        else:
            self.yield_for_replicator_connected(repl)
        return repl

    def yield_for_replicator_connected(self, repl, max_times=5, sleep_time=0.5):
        count = 0
        # Sleep until replicator gets connected
        activity_level = self.getActivitylevel(repl)
        while count < max_times:
            time.sleep(sleep_time)
            if activity_level == "connecting":
                count += 1
            else:
                break

    def wait_until_replicator_idle(self, repl, err_check=True, max_times=150, sleep_time=2, max_timeout=600):
        count = 0
        idle_count = 0
        max_idle_count = 3

        # Load the current replicator config to decide retry strategy
        repl_config = self.getConfig(repl)
        isContinous = self.isContinuous(repl_config)
        log_info("The current replicator sets continuous to {}".format(isContinous))

        # Sleep until replicator completely processed
        activity_level = self.getActivitylevel(repl)
        begin_timestamp = time.time()
        while count < max_times:
            log_info("Activity level: {}".format(activity_level))
            log_info("total vs completed = {} vs {} ".format(self.getCompleted(repl), self.getTotal(repl)))
            log_info("count is  {}".format(count))
            log_info("Activity level {}".format(activity_level))
            time.sleep(sleep_time)
            if activity_level == "offline" or activity_level == "connecting" or activity_level == "busy":
                count += 1
                idle_count = 0
            else:
                if activity_level == "idle":
                    if (self.getCompleted(repl) < self.getTotal(repl)) and self.getTotal(repl) != 0:
                        count += 1
                    else:
                        idle_count += 1
                        time.sleep(sleep_time)
                        if idle_count > max_idle_count:
                            break
            cur_timestamp = time.time()
            if err_check:
                err = self.getError(repl)
                if err is not None and err != 'nil' and err != -1:
                    if not isContinous:
                        raise Exception("Error while replicating", err)
                    if is_replicator_in_connection_retry(err) and (cur_timestamp - begin_timestamp) < max_timeout:
                        log_info("Replicator connection is retrying, please wait ......")
                    else:
                        raise Exception("Error while replicating", err)

            activity_level = self.getActivitylevel(repl)
            total = self.getTotal(repl)
            completed = self.getCompleted(repl)
            if activity_level == "stopped":
                if completed < total:
                    raise Exception("replication progress is not completed")
                else:
                    break
            if total < completed and total <= 0:
                raise Exception("total is less than completed")

    def create_session_configure_replicate(self, baseUrl, sg_admin_url, sg_db, username, password,
                                           channels, sg_client, cbl_db, sg_blip_url, replication_type=None,
                                           continuous=True, max_retries=None, max_retry_wait_time=None, encryptor=None):

        authenticator = Authenticator(baseUrl)
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
        session = cookie, session_id
        replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
        repl_config = self.configure(cbl_db, sg_blip_url, continuous=continuous, channels=channels,
                                     replication_type=replication_type,
                                     replicator_authenticator=replicator_authenticator,
                                     max_retries=max_retries, max_retry_wait_time=max_retry_wait_time, encryptor=encryptor)
        repl = self.create(repl_config)
        self.start(repl)
        self.wait_until_replicator_idle(repl)

        return session, replicator_authenticator, repl

    def resetCheckPoint(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_resetCheckpoint", args)
