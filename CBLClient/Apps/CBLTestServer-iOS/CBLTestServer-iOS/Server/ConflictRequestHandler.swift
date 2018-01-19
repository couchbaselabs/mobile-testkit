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
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////
        // Conflict //
        //////////////
        case "conflict_resolver":
            let conflict_type: String? = args.get(name: "conflict_type")
            if conflict_type == "mine" {
                return ReplicationMine()
                
            } else if conflict_type == "theirs" {
                return ReplicationTheirs()
            }
            else if conflict_type == "base" {
                return ReplicationBase()
            }
            else {
                func resolve(conflict: Conflict) -> Document? {
                    return nil
                }
            }

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return ConflictRequestHandler.VOID
    }
}

class ReplicationMine: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.mine
    }
}

class ReplicationTheirs: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.theirs
    }
}

class ReplicationBase: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.base
    }
}

class GiveUp: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return nil
    }
}


