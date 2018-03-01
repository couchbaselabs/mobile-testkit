import time
import os

from CBLClient.Client import Client
from CBLClient.Args import Args
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from keywords.constants import SYNC_GATEWAY_CERT
from utilities.cluster_config_utils import sg_ssl_enabled


class Replication(object):
    '''
    classdocs
    '''
    baseUrl = None

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

    def configure(self, source_db, target_url=None, target_db=None, replication_type="push_pull", continuous=False,
                  channels=None, documentIDs=None, replicator_authenticator=None, headers=None):
        args = Args()
        args.setMemoryPointer("source_db", source_db)
        args.setBoolean("continuous", continuous)
        if channels is not None:
            args.setArray("channels", channels)

        if documentIDs is not None:
            args.setArray("documentIDs", documentIDs)

        if replicator_authenticator is not None:
            args.setMemoryPointer("authenticator", replicator_authenticator)

        if replication_type is None:
            replication_type = "push_pull"
            args.setString("replication_type", replication_type)

        if headers is not None:
            args.setDictionary("headers", headers)

        if target_url is not None:
            args.setString("target_url", target_url)

        if target_db is not None:
            args.setMemoryPointer("target_db", target_db)

        cluster_config = os.environ["CLUSTER_CONFIG"]
        if sg_ssl_enabled(cluster_config):
            cert_file = os.path.abspath("{}/sg_cert.pem".format(SYNC_GATEWAY_CERT))
            f = open(cert_file)
            cert = f.read()

            args.setString("pinnedservercert", cert)

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

#     Protected method now
#     def copy(self, configuration):
#         args = Args()
#         args.setMemoryPointer("configuration", configuration)
#         return self._client.invokeMethod("replicatorConfiguration_copy", args)

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

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("replicator_create", args)

    def getConfig(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_config", args)

#     Same as status method
#     def getStatus(self, replicator):
#         args = Args()
#         args.setMemoryPointer("replicator", replicator)
#         return self._client.invokeMethod("replicator_getStatus", args)

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

#     Not available any more
#     def networkReachable(self, replicator):
#         args = Args()
#         args.setMemoryPointer("replicator", replicator)
#         return self._client.invokeMethod("replicator_networkReachable", args)
#
#     def networkUnreachable(self, replicator):
#         args = Args()
#         args.setMemoryPointer("replicator", replicator)
#         return self._client.invokeMethod("replicator_networkUnreachable", args)

    def start(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_start", args)

    def stop(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        # return self._client.invokeMethod("replicator_stop", args)
        self._client.invokeMethod("replicator_stop", args)
        max_times = 15
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
#         error = self._client.invokeMethod("replicator_getError", args)
#         if error.__contains__("@"):
#             error = None
        return self._client.invokeMethod("replicator_getError", args)

    def getChangesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("replicator_changeListenerChangesCount", args)

    def getChangesChangeListener(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        # args.setInt("index", index)
        return self._client.invokeMethod("replicator_changeListenerGetChanges", args)

    def configure_and_replicate(self, source_db, replicator_authenticator, target_db=None, target_url=None, replication_type="push_pull", continuous=True,
                                channels=None, err_check=True):
        if target_db is None:
            repl_config = self.configure(source_db, target_url=target_url, continuous=continuous,
                                         replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        else:
            repl_config = self.configure(source_db, target_db=target_db, continuous=continuous,
                                         replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        repl = self.create(repl_config)
        self.start(repl)
        self.wait_until_replicator_idle(repl, err_check)
        return repl

    def wait_until_replicator_idle(self, repl, err_check=True):
        max_times = 10
        count = 0
        # Sleep until replicator completely processed
        activity_level = self.getActivitylevel(repl)
        while activity_level != "idle" and count < max_times:
            log_info("Activity level: {}".format(activity_level))
            time.sleep(2)
            if activity_level == "idle" or activity_level == "offline" or activity_level == "connecting":
                count += 1
            if activity_level == "stopped":
                break
            if err_check:
                err = self.getError(repl)
                if err is not None and err != 'nil' and err != -1:
                    raise Exception("Error while replicating", err)
            activity_level = self.getActivitylevel(repl)

    def create_session_configure_replicate(self, baseUrl, sg_admin_url, sg_db, username, password,
                                           channels, sg_client, cbl_db, sg_blip_url, replication_type=None, continuous=True):

        authenticator = Authenticator(baseUrl)
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
        session = cookie, session_id
        replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
        # replicator_authenticator = authenticator.authentication(username=username, password=password, authentication_type="basic")
        repl_config = self.configure(cbl_db, sg_blip_url, continuous=continuous, channels=channels, replication_type=replication_type, replicator_authenticator=replicator_authenticator)
        repl = self.create(repl_config)
        self.start(repl)
        self.wait_until_replicator_idle(repl)

        return session, replicator_authenticator, repl


"""
    def configure(self, source_db, target_url=None, target_db=None,
                  replication_type="push_pull", continuous=False,
                  channels=None, document_ids=None,
                  replicator_authenticator=None):
        args = Args()
        args.setString("replication_type", replication_type)
        repl_config_obj = ReplicatorConfiguration(self.base_url)
        if target_url:
            self.config = repl_config_obj.create(source_db, target_url=target_url)
        elif target_db:
            self.config = repl_config_obj.create(source_db, target_db=target_db)

        if channels is not None:
            repl_config_obj.setChannels(self.config, channels)

        if document_ids is not None:
            repl_config_obj.setDocumentIDs(self.config, document_ids)

        if replicator_authenticator is not None:
            repl_config_obj.setAuthenticator(self.config, replicator_authenticator)

        repl_config_obj.setContinuous(self.config, continuous)
        repl_config_obj.setReplicatorType(self.config, replication_type)
        return self.create(self.config)
"""
