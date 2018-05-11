//
//  ResultRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class ResultRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ////////////
        // Result //
        ////////////
        case "resultRequest_nextResult":
            let query_result_set: ResultSet = args.get(name: "query_result_set")!
            
            return query_result_set.next()
            
        case "resultRequest_getString":
            let query_result: Result = args.get(name: "query_result")!
            let key: String = args.get(name: "key")!
            
            return query_result.string(forKey: key)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
