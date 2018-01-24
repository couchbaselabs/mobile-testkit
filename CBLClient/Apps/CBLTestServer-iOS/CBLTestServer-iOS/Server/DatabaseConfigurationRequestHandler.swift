//
//  DatabaseConfigurationRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 1/23/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class DatabaseConfigurationRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {

        /////////////////////////////
        // Database Configuration //
        ////////////////////////////
        case "databaseConfiguration_configure":
            let directory: String? = args.get(name:"directory")!
            let conflictResolver : ConflictResolver? = args.get(name:"conflictResolver")!
            let encryptionKey: EncryptionKey? = args.get(name:"encryptionKey")!
            let fileProtection: NSData.WritingOptions? = args.get(name: "fileProtection")!
            let builder = DatabaseConfiguration.Builder()
            if directory != nil{
                builder.setDirectory(directory!)
            }
            if conflictResolver != nil{
                builder.setConflictResolver(conflictResolver!)
            }
            if encryptionKey != nil{
                builder.setEncryptionKey(encryptionKey!)
            }
            if fileProtection != nil{
                builder.setFileProtection(fileProtection!)
            }
            return builder.build()
            
        case "databaseConfiguration_getConflictResolver":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.conflictResolver
            
        case "databaseConfiguration_getDirectory":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.directory
            
        case "databaseConfiguration_getEncryptionKey":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.encryptionKey
            
        case "databaseConfiguration_setConflictResolver":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let conflictResolver: ConflictResolver = args.get(name: "conflictResolver")!
            return config.setConflictResolver(conflictResolver)
            
        case "databaseConfiguration_setDirectory":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let directory: String = args.get(name: "directory")!
            return config.setDirectory(directory)
            
        case "databaseConfiguration_setEncryptionKey":
            let config: DatabaseConfiguration.Builder = args.get(name: "config")!
            let key: EncryptionKey = args.get(name: "key")!
            return config.setEncryptionKey(key)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DatabaseConfigurationRequestHandler.VOID
  }
}


