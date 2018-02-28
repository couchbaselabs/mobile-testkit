//
//  CollationRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class CollationRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ///////////////
        // Collation //
        ///////////////
        case "collation_ascii":
            let ignoreCase: Bool = args.get(name: "ignoreCase")!
            
            return Collation.ascii().ignoreCase(ignoreCase)
            
        case "collation_unicode":
            let ignoreCase: Bool = args.get(name: "ignoreCase")!
            let ignoreAccents: Bool = args.get(name: "ignoreAccents")!
            
            return Collation.unicode().ignoreCase(ignoreCase).ignoreAccents(ignoreAccents)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
