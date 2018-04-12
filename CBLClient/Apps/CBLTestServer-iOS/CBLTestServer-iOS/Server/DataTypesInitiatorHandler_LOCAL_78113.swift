//
//  DataTypesInitiatorHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class DataTypesInitiatorHandler {
    public static let VOID = NSObject()
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DataTypesInitiatorHandler.VOID
    }
}
