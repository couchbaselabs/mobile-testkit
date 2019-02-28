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
            let password: String? = args.get(name:"password")
            #if COUCHBASE_ENTERPRISE
            let encryptionKey: EncryptionKey? = password != nil ? EncryptionKey.password(password!) : nil
            #endif
            let config = DatabaseConfiguration()
            if directory != nil {
                config.directory = directory!
            }

            #if COUCHBASE_ENTERPRISE
            if encryptionKey != nil {
                config.encryptionKey = encryptionKey!
            }
            #endif
            return config

        case "databaseConfiguration_getDirectory":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.directory

        #if COUCHBASE_ENTERPRISE
        case "databaseConfiguration_getEncryptionKey":
            let config: DatabaseConfiguration = args.get(name: "config")!
            return config.encryptionKey
            
        case "databaseConfiguration_setEncryptionKey":
            let config: DatabaseConfiguration = args.get(name: "config")!
            let password: String? = args.get(name:"password")!
            let encryptionKey: EncryptionKey? = EncryptionKey.password(password!)
            config.encryptionKey = encryptionKey
            return config
        #endif
            
        case "databaseConfiguration_setDirectory":
            let config: DatabaseConfiguration = args.get(name: "config")!
            let directory: String = args.get(name: "directory")!
            config.directory = directory
            return config
            
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
  }
}


