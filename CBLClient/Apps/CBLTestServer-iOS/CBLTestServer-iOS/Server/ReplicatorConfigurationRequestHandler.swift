//
//  ReplicatorConfigurationRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/6/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class ReplicatorConfigurationRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        /////////////////////////////
        // ReplicatorConfiguration //
        /////////////////////////////
            
        // TODO: Change client to expect replicator config, not the builder.
        case "replicatorConfiguration_create":
            let sourceDb: Database = args.get(name: "sourceDb")!
            let targetURI: String? = args.get(name: "targetURI")!
            let targetDb: Database? = args.get(name: "targetDb")!
            var target: Endpoint?
            
            #if COUCHBASE_ENTERPRISE
            if (targetDb != nil) {
                target = DatabaseEndpoint(database: targetDb!)
            }
            #endif
            
            if (targetURI != nil) {
                target = URLEndpoint(url: URL(string: targetURI!)!)
            }
            
            if (target == nil) {
                throw RequestHandlerError.InvalidArgument("Target database or URL should be provided.")
            }
            
            return ReplicatorConfiguration(database: sourceDb, target: target!)
            
        case "replicatorConfiguration_configure":
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authValue: AnyObject? = args.get(name: "authenticator")
            let authenticator: Authenticator? = authValue as? Authenticator
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            let pinnedservercert: String? = args.get(name: "pinnedservercert")!
            let pull_filter: Bool? = args.get(name: "pull_filter")!
            let push_filter: Bool? = args.get(name: "push_filter")!
            let filter_callback_func: String? = args.get(name: "filter_callback_func")
            let conflict_resolver: String? = args.get(name: "conflict_resolver")
            
            var replicatorType = ReplicatorType.pushAndPull
            
            if let type = replication_type {
                if type == "push" {
                    replicatorType = .push
                } else if type == "pull" {
                    replicatorType = .pull
                } else {
                    replicatorType = .pushAndPull
                }
            }
            var config: ReplicatorConfiguration
            if (source_db == nil){
                throw RequestHandlerError.InvalidArgument("No source db provided")
            }

            var target: Endpoint?
            if (target_url != nil) {
                do {
                    try tryCatch {
                        target = URLEndpoint(url: URL(string: target_url!)!)
                    }
                } catch let error as NSError {
                    if let exception = error.userInfo["exception"] as? NSException {
                        if let reason = exception.reason {
                            throw RequestHandlerError.InvalidArgument("\(reason)")
                        } else {
                            throw RequestHandlerError.InvalidArgument("Unknown CBL Exception")
                        }
                    }
                }
            }
            
            #if COUCHBASE_ENTERPRISE
                let targetDatabase: Database? = args.get(name: "target_db")
                if (targetDatabase != nil) {
                    target = DatabaseEndpoint(database: targetDatabase!)
                    config = ReplicatorConfiguration(database: source_db!, target: target!)
                }
            #endif

            if (target == nil) {
                throw RequestHandlerError.InvalidArgument("target url or database should be provided.")
            }
            config = ReplicatorConfiguration(database: source_db!, target: target!)
            config.replicatorType = replicatorType
            if continuous != nil {
                config.continuous = continuous!
            } else {
                config.continuous = false
            }
            if headers != nil {
                config.headers = headers
            }
            config.authenticator = authenticator
            if channels != nil {
                config.channels = channels
            }
            if documentIDs != nil {
                config.documentIDs = documentIDs
            }
            if pinnedservercert != nil {
                let path = Bundle(for: type(of:self)).path(forResource: pinnedservercert, ofType: "cer")
                let data = try! NSData(contentsOfFile: path!, options: [])
                let certificate = SecCertificateCreateWithData(nil, data)
                config.pinnedServerCertificate = certificate
            }
            if pull_filter != false {
                if filter_callback_func == "boolean" {
                    config.pullFilter = _replicatorBooleanFilterCallback;
                } else if filter_callback_func == "deleted" {
                    config.pullFilter = _replicatorDeletedFilterCallback;
                } else if filter_callback_func == "access_revoked" {
                    config.pullFilter = _replicatorAccessRevokedCallback;
                } else {
                    config.pullFilter = _defaultReplicatorFilterCallback;
                }
            }
            if push_filter != false {
                if filter_callback_func == "boolean" {
                    config.pushFilter = _replicatorBooleanFilterCallback;
                } else if filter_callback_func == "deleted" {
                    config.pushFilter = _replicatorDeletedFilterCallback;
                } else if filter_callback_func == "access_revoked" {
                    config.pushFilter = _replicatorAccessRevokedCallback;
                } else {
                    config.pushFilter = _defaultReplicatorFilterCallback;
                }
            }
            switch conflict_resolver {
                case "local_wins":
                    config.conflictResolver = LocalWinCustomConflictResolver();
                    break
                case "remote_wins":
                    config.conflictResolver = RemoteWinCustomConflictResolver();
                    break;
                case "null":
                    config.conflictResolver = NullWinCustomConflictResolver();
                    break;
                case "merge":
                    config.conflictResolver = MergeWinCustomConflictResolver();
                    break;
                default:
                    config.conflictResolver = ConflictResolver.default
                    break;
            }
            return config
        
        case "replicatorConfiguration_getAuthenticator":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.authenticator
            
        case "replicatorConfiguration_getChannels":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.channels
            
        case "replicatorConfiguration_getDatabase":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.database
            
        case "replicatorConfiguration_getDocumentIDs":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.documentIDs
            
        case "replicatorConfiguration_getPinnedServerCertificate":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.pinnedServerCertificate
            
        case "replicatorConfiguration_getReplicatorType":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.replicatorType.rawValue
            
        case "replicatorConfiguration_getTarget":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.target
            
        case "replicatorConfiguration_isContinuous":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.continuous
        
        case "replicatorConfiguration_setAuthenticator":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let authenticator: Authenticator = args.get(name: "authenticator")!
            replicatorConfiguration.authenticator = authenticator
        
        case "replicatorConfiguration_setChannels":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let channels: [String] = args.get(name: "channels")!
            replicatorConfiguration.channels = channels
        
        case "replicatorConfiguration_setContinuous":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let continuous: Bool = args.get(name: "continuous")!
            replicatorConfiguration.continuous = continuous
        
        case "replicatorConfiguration_setDocumentIDs":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let documentIds: [String] = args.get(name: "documentIds")!
            replicatorConfiguration.documentIDs = documentIds
            
        case "replicatorConfiguration_setPinnedServerCertificate":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let cert: SecCertificate? = args.get(name: "cert")!
            replicatorConfiguration.pinnedServerCertificate = cert
        
        case "replicatorConfiguration_setReplicatorType":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let type: String = args.get(name: "replType")!
            var replicatorType: ReplicatorType
            switch (type) {
                case "push":
                    replicatorType = ReplicatorType.push
                    break
                case "pull":
                    replicatorType = ReplicatorType.pull
                    break
                default:
                    replicatorType = ReplicatorType.pushAndPull
            }
            replicatorConfiguration.replicatorType = replicatorType

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorConfigurationRequestHandler.VOID
    }


    private func _replicatorBooleanFilterCallback(document: Document, flags: DocumentFlags) -> Bool {
        let key:String = "new_field_1"
        if document.contains(key){
            let value:Bool = document.boolean(forKey: key)
            return value;
        }
        return true
    }
    
    private func _defaultReplicatorFilterCallback(document: Document, flags: DocumentFlags) -> Bool {
        return true;
    }
    
    private func _replicatorDeletedFilterCallback(document: Document, documentFlags: DocumentFlags) -> Bool {
        if (documentFlags.rawValue == 1) {
            return false
        }
        return true
    }
    
    private func _replicatorAccessRevokedCallback(document: Document, documentFlags: DocumentFlags) -> Bool {
        if (documentFlags.rawValue == 2) {
            return false
        }
        return true
    }
}

private class LocalWinCustomConflictResolver: ConflictResolverProtocol {
    func resolve(conflict: Conflict) -> Document? {
        let localDoc = conflict.localDocument!
        let remoteDoc = conflict.remoteDocument!
        let docId = conflict.documentID
        let remoteDocId = remoteDoc.id
        let localDocId = localDoc.id
        if remoteDocId != localDocId {
            print("Remote docId and local docId are different")
        }
        if remoteDocId != docId {
            print("Remote docId doesn't match with conflict docId")
        }
        if localDocId != docId {
            print("Local docId doesn't match with conflict docId")
        }
        return localDoc
    }
}

private class RemoteWinCustomConflictResolver: ConflictResolverProtocol{
    func resolve(conflict: Conflict) -> Document? {
        let localDoc = conflict.localDocument!
        let remoteDoc = conflict.remoteDocument!
        let docId = conflict.documentID
        let remoteDocId = remoteDoc.id
        let localDocId = localDoc.id
        if remoteDocId != localDocId {
            print("Remote docId and local docId are different")
        }
        if remoteDocId != docId {
            print("Remote docId doesn't match with conflict docId")
        }
        if localDocId != docId {
            print("Local docId doesn't match with conflict docId")
        }
        return remoteDoc
    }
}

private class NullWinCustomConflictResolver: ConflictResolverProtocol{
    func resolve(conflict: Conflict) -> Document? {
        let localDoc = conflict.localDocument!
        let remoteDoc = conflict.remoteDocument!
        let docId = conflict.documentID
        let remoteDocId = remoteDoc.id
        let localDocId = localDoc.id
        if remoteDocId != localDocId {
            print("Remote docId and local docId are different")
        }
        if remoteDocId != docId {
            print("Remote docId doesn't match with conflict docId")
        }
        if localDocId != docId {
            print("Local docId doesn't match with conflict docId")
        }
        return nil
    }
}

private class MergeWinCustomConflictResolver: ConflictResolverProtocol{
    func resolve(conflict: Conflict) -> Document? {
        let localDoc = conflict.localDocument!
        let remoteDoc = conflict.remoteDocument!
        let docId = conflict.documentID
        let remoteDocId = remoteDoc.id
        let localDocId = localDoc.id
        if remoteDocId != localDocId {
            print("Remote docId and local docId are different")
        }
        if remoteDocId != docId {
            print("Remote docId doesn't match with conflict docId")
        }
        if localDocId != docId {
            print("Local docId doesn't match with conflict docId")
        }
        let newDoc = localDoc.toMutable()
        let remoteDocMap = remoteDoc.toDictionary()
        for (key, value) in remoteDocMap {
            if !newDoc.contains(key) {
                newDoc.setValue(value, forKey: key)
            }
        }
        return newDoc
    }
}
