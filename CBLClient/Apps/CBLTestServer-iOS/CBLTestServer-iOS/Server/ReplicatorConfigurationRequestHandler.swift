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
            let targetDb: Database? = args.get(name: "targetDb")!
            let targetURI: String? = args.get(name: "targetURI")!
            
            if (targetDb != nil){
                let target = DatabaseEndpoint(database: targetDb!)
                return ReplicatorConfiguration(database: sourceDb, target: target)
            } else if (targetURI != nil){
                let target = URLEndpoint(url: URL(string: targetURI!)!)
                return ReplicatorConfiguration(database: sourceDb, target: target)
            } else {
                throw RequestHandlerError.InvalidArgument("Incorrect configuration parameter provided")
            }
            
        case "replicatorConfiguration_configure":
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
            let targetDatabase: Database? = args.get(name: "target_db")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            
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
            let config: ReplicatorConfiguration!
            //let target_converted_url: URL? = URL(string: target_url!)
            if (source_db != nil && target_url != nil) {
                let target = URLEndpoint(url: URL(string: target_url!)!)
                config = ReplicatorConfiguration(database: source_db!, target: target)
            }
            else if (source_db != nil && targetDatabase != nil) {
                let target = DatabaseEndpoint(database: targetDatabase!)
                config = ReplicatorConfiguration(database: source_db!, target: target)
            }
            else{
                    throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }
            
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
            if(conflictResolver != nil){
                config.conflictResolver = conflictResolver!
            }
            if channels != nil {
                config.channels = channels
            }
            if documentIDs != nil {
                config.documentIDs = documentIDs
            }
            return config
        
        // TODO: Remove
        /*
        case "replicatorConfiguration_configureLocalDb":
            let source_db: Database? = args.get(name: "source_db")
            let targetDatabase: Database? = args.get(name: "target_db")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            
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
            
            if (source_db != nil && targetDatabase != nil) {
                let target = DatabaseEndpoint(withDatabase: targetDatabase!)
                let builder = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)
                
                builder.setReplicatorType(replicatorType)
                if continuous != nil {
                    builder.setContinuous(continuous!)
                } else {
                    builder.setContinuous(false)
                }
                if authenticator != nil {
                    builder.setAuthenticator(authenticator)
                }
                if headers != nil {
                    builder.setHeaders(headers)
                }
                if channels != nil {
                    builder.setChannels(channels)
                }
                if conflictResolver != nil {
                    builder.setConflictResolver(conflictResolver!)
                }
                if documentIDs != nil {
                    builder.setDocumentIDs(documentIDs)
                }
                
                return builder.build()
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target DB provided")
            }
        */
        case "replicatorConfiguration_getAuthenticator":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.authenticator
            
        case "replicatorConfiguration_getChannels":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.channels
            
        case "replicatorConfiguration_getConflictResolver":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            return replicatorConfiguration.conflictResolver
            
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
        
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setAuthenticator":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let authenticator: Authenticator = args.get(name: "authenticator")!
            replicatorConfiguration.authenticator = authenticator
        
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setChannels":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let channels: [String] = args.get(name: "channels")!
            replicatorConfiguration.channels = channels
        
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setConflictResolver":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let conflictResolver: ConflictResolver = args.get(name: "conflictResolver")!
            replicatorConfiguration.conflictResolver = conflictResolver
        
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setContinuous":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let continuous: Bool = args.get(name: "continuous")!
            replicatorConfiguration.continuous = continuous
        
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setDocumentIDs":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let documentIds: [String] = args.get(name: "documentIds")!
            replicatorConfiguration.documentIDs = documentIds
            
        // TODO: change the argument from builder to config in client API call
        case "replicatorConfiguration_setPinnedServerCertificate":
            let replicatorConfiguration: ReplicatorConfiguration = args.get(name: "configuration")!
            let cert: SecCertificate? = args.get(name: "cert")!
            replicatorConfiguration.pinnedServerCertificate = cert
        
        // TODO: change the argument from builder to config in client API call
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
}
