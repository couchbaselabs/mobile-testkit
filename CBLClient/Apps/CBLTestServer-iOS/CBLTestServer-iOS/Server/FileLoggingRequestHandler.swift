//
//  FileLoggingRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Hemant on 27/02/19.
//  Copyright © 2019 Hemant Rajput. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class FileLoggingRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
            /////////////////
            // CBL Logging //
            /////////////////
        case "logging_configure":
            let max_rotate_count: Int = args.get(name: "max_rotate_count")!
            let max_size_temp: NSNumber = args.get(name: "max_size")!
            let max_size: UInt64 = UInt64(truncating: max_size_temp)
            let log_level: String = args.get(name: "log_level")!
            let plain_text: Bool = args.get(name: "plain_text")!
            var directory: String = args.get(name: "directory")!
            if (directory.isEmpty) {
                directory = NSHomeDirectory() + "/logs" + String(Date().timeIntervalSince1970)
                print("File logging configured at : " + directory)
            }
            
            let config: LogFileConfiguration = LogFileConfiguration.init(directory: directory)
            if (max_rotate_count > 1) {
                config.maxRotateCount = max_rotate_count
            }
            if (max_size > 512000) {
                config.maxSize = max_size
            }
            config.usePlainText = plain_text
            Database.log.file.config = config
            switch log_level {
            case "debug":
                Database.log.file.level = LogLevel.debug
                break
            case "verbose":
                Database.log.file.level = LogLevel.verbose
                break
            case "error":
                Database.log.file.level = LogLevel.error
                break
            case "info":
                Database.log.file.level = LogLevel.info
                break
            case "warning":
                Database.log.file.level = LogLevel.warning
                break
            default:
                Database.log.file.level = LogLevel.none
            }
            return config

        case "logging_getPlainTextStatus":
            return Database.log.file.config?.usePlainText

        case "logging_getMaxRotateCount":
            return Database.log.file.config?.maxRotateCount

        case "logging_getMaxSize":
            return Database.log.file.config?.maxSize

        case "logging_getLogLevel":
            return Database.log.file.level.rawValue

        case "logging_getConfig":
            return Database.log.file.config

        case "logging_setPlainTextStatus":
            let config: LogFileConfiguration = args.get(name: "config")!
            let plain_text: Bool = args.get(name: "plain_text")!
            config.usePlainText = plain_text
            return config

        case "logging_setMaxRotateCount":
            let config: LogFileConfiguration = args.get(name: "config")!
            let max_rotate_count: Int = args.get(name: "max_rotate_count")!
            config.maxRotateCount = max_rotate_count
            return config

        case "logging_setMaxSize":
            let config: LogFileConfiguration = args.get(name: "config")!
            let max_size_temp: NSNumber = args.get(name: "max_size")!
            let max_size: UInt64 = UInt64(truncating: max_size_temp)
            config.maxSize = max_size
            return config

        case "logging_setConfig":
            var directory: String = args.get(name: "directory")!
            if (directory.isEmpty) {
                directory = NSHomeDirectory() + "/logs" + String(Date().timeIntervalSince1970)
                print("File logging configured at : " + directory)
            }
            let config: LogFileConfiguration = LogFileConfiguration.init(directory: directory)
            Database.log.file.config = config
            return config

        case "logging_setLogLevel":
            let config: LogFileConfiguration = args.get(name: "config")!
            let log_level: String = args.get(name: "log_level")!
            switch log_level {
            case "debug":
                Database.log.file.level = LogLevel.debug
                break
            case "verbose":
                Database.log.file.level = LogLevel.verbose
                break
            case "error":
                Database.log.file.level = LogLevel.error
                break
            case "info":
                Database.log.file.level = LogLevel.info
                break
            case "warning":
                Database.log.file.level = LogLevel.warning
                break
            default:
                Database.log.file.level = LogLevel.none
            }
            return config

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
