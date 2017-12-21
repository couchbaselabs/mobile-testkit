//
//  DocumentRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum DocumentRequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class DocumentRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////
        // Document //
        //////////////
        case "document_create":
            let id: String? = (args.get(name: "id"))
            let dictionary: [String: Any]? = (args.get(name: "dictionary"))
            return MutableDocument(withID: id, data: dictionary)
            
        case "document_delete":
            let database: Database = (args.get(name:"database"))!
            let document: Document = args.get(name:"document")!
            
            try! database.deleteDocument(document)
            
        case "document_getId":
            let document: Document = (args.get(name: "document"))!
            
            return document.id
            
        case "document_getString":
            let document: Document = (args.get(name: "document"))!
            let property: String = (args.get(name: "property"))!
            
            return document.string(forKey: property)
            
        case "document_setString":
            let document: MutableDocument = (args.get(name: "document"))!
            let property: String = (args.get(name: "property"))!
            let string: String = (args.get(name: "string"))!
            
            document.setString(property, forKey: string)

        default:
            throw DocumentRequestHandlerError.MethodNotFound(method)
        }
        return DocumentRequestHandler.VOID;
    }
}
