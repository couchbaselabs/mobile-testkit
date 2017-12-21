//
//  DataTypesInitiatorHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum DataTypesInitiatorHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class DataTypesInitiatorHandler {
    public static let VOID = NSObject()
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        default:
            throw DataTypesInitiatorHandlerError.MethodNotFound(method)
        }
        return DataTypesInitiatorHandler.VOID;
    }
}
