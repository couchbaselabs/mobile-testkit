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
        case "replicatorConfiguration_create":
            let sourceDb: Database = args.get(name: "sourceDb")!
            let targetDb: Database? = args.get(name: "targetDb")!
            let targetURI: String? = args.get(name: "targetURI")!
            
            if (targetDb != nil){
                let target = DatabaseEndpoint(withDatabase: targetDb!)
                return ReplicatorConfiguration.Builder(withDatabase: sourceDb, target: target)
            } else if (targetURI != nil){
                let target = URLEndpoint(withURL: URL(string: targetURI!)!)
                return ReplicatorConfiguration.Builder(withDatabase: sourceDb, target: target)
            } else {
                throw RequestHandlerError.InvalidArgument("Incorrect configuration parameter provided")
            }
            
        case "replicatorConfiguration_configureRemoteDbUrl":
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
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
            
            //let target_converted_url: URL? = URL(string: target_url!)
            if (source_db != nil && target_url != nil) {
                let target = URLEndpoint(withURL: URL(string: target_url!)!)
                
                let builder = ReplicatorConfiguration.Builder(withDatabase: source_db!, target: target)
                builder.setReplicatorType(replicatorType)
                if continuous != nil {
                    builder.setContinuous(continuous!)
                } else {
                    builder.setContinuous(false)
                }
                if headers != nil {
                    builder.setHeaders(headers)
                }
                builder.setAuthenticator(authenticator)
                if(conflictResolver != nil){
                    builder.setConflictResolver(conflictResolver!)
                }
                if channels != nil {
                    builder.setChannels(channels)
                }
                if documentIDs != nil {
                    builder.setDocumentIDs(documentIDs)
                }
                return builder.build()
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }
            
            
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
            
        case "replicatorConfiguration_setAuthenticator":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let authenticator: Authenticator = args.get(name: "authenticator")!
            replicatorConfiguration.setAuthenticator(authenticator)
            
        case "replicatorConfiguration_setChannels":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let channels: [String] = args.get(name: "channels")!
            replicatorConfiguration.setChannels(channels)
            
        case "replicatorConfiguration_setConflictResolver":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let conflictResolver: ConflictResolver = args.get(name: "conflictResolver")!
            replicatorConfiguration.setConflictResolver(conflictResolver)
            
        case "replicatorConfiguration_setContinuous":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let continuous: Bool = args.get(name: "continuous")!
            replicatorConfiguration.setContinuous(continuous)
            
        case "replicatorConfiguration_setDocumentIDs":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let documentIds: [String] = args.get(name: "documentIds")!
            replicatorConfiguration.setDocumentIDs(documentIds)
            
        case "replicatorConfiguration_setPinnedServerCertificate":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
            let cert: SecCertificate? = args.get(name: "cert")!
            replicatorConfiguration.setPinnedServerCertificate(cert)
            
        case "replicatorConfiguration_setReplicatorType":
            let replicatorConfiguration: ReplicatorConfiguration.Builder = args.get(name: "configuration")!
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
            replicatorConfiguration.setReplicatorType(replicatorType)


        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ReplicatorConfigurationRequestHandler.VOID
    }
}
