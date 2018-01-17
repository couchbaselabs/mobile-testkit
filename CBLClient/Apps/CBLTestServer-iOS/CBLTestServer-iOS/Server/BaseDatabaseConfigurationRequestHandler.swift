//
//  BaseDatabaseConfigurationRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class BasicDatabaseConfigurationRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ///////////////////////////
        // DatabaseConfiguration //
        ///////////////////////////
        case "baseDatabaseConfiguration_create":
            return DatabaseConfiguration.Builder()

        case "getConflictResolver":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.conflictResolver
            
        case "getDirectory":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.directory
            
        case "getEncryptionKey":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.encryptionKey
            
        case "baseDatabaseConfiguration_setConflictResolver":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let conflictResolver: ConflictResolver = args.get(name: "conflictResolver")!
            return config.setConflictResolver(conflictResolver)
            
        case "baseDatabaseConfiguration_setDirectory":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let directory: String = args.get(name: "directory")!
            return config.setDirectory(directory)

        case "baseDatabaseConfiguration_setEncryptionKey":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let key: EncryptionKey = args.get(name: "key")!
            return config.setEncryptionKey(key)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return BasicDatabaseConfigurationRequestHandler.VOID
    }
}
