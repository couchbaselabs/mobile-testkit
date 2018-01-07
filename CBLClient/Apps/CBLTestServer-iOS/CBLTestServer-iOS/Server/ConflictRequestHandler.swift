//
//  ConflictRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/26/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class ConflictRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////
        // Conflict //
        //////////////
        case "conflict_getBase":
            let conflict: Conflict = args.get(name: "conflict")!
            return conflict.base
        
        case "conflict_getMine":
            let conflict: Conflict = args.get(name: "conflict")!
            return conflict.mine

        
        case "conflict_getTheirs":
            let conflict: Conflict = args.get(name: "conflict")!
            return conflict.theirs

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ConflictRequestHandler.VOID
    }
}

