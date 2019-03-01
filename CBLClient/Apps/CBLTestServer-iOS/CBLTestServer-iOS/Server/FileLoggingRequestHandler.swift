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
            if (directory == "") {
                directory = NSHomeDirectory() + "/logs" + String(Date().timeIntervalSince1970)
                print("File logging configured at : " + directory)
            }
            
            let config: LogFileConfiguration = LogFileConfiguration.init(directory: directory)
            if (max_rotate_count > 0) {
                config.maxRotateCount = max_rotate_count
            }
            if (max_size > 0) {
                config.maxSize = max_size
            }
            config.usePlainText = plain_text
            Database.log.file.config = config
            if (log_level == "debug") {
                Database.log.file.level = LogLevel.debug
            } else if  (log_level == "verbose") {
                Database.log.file.level = LogLevel.verbose
            } else if  (log_level == "error") {
                Database.log.file.level = LogLevel.error
            } else if  (log_level == "info") {
                Database.log.file.level = LogLevel.info
            } else if  (log_level == "warning") {
                Database.log.file.level = LogLevel.warning
            } else {
                Database.log.file.level = LogLevel.none
            }
            return directory

        case "logging_getPlainTextStatus":
            return Database.log.file.config?.usePlainText

        case "logging_getMaxRotateCount":
            return Database.log.file.config?.maxRotateCount

        case "logging_getMaxSize":
            return Database.log.file.config?.maxSize

        case "logging_getLogLevel":
            return Database.log.file.level.rawValue

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
