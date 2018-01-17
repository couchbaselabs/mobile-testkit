//
//  SelectResultRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class SelectResultRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////////
        // selectResult //
        //////////////////
        case "selectResult_expressionCreate":
            let expression: Expression = args.get(name: "expression")!
            
            return SelectResult.expression(expression)
            
        case "selectResult_all":
            return SelectResult.all()

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return SelectResultRequestHandler.VOID
    }
}
