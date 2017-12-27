//
//  Server.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/24/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum ServerError: Error {
    case MethodNotImplemented(String)
}

enum RequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}

public class Server {
    let kPort:UInt = 8989
    let server: GCDWebServer!
    let dictionaryRequestHandler: DictionaryRequestHandler!
    let queryRequestHandler: QueryRequestHandler!
    let databaseRequestHandler: DatabaseRequestHandler!
    let documentRequestHandler: DocumentRequestHandler!
    let replicatorRequestHandler: ReplicatorRequestHandler!
    let dataTypesInitiatorHandler: DataTypesInitiatorHandler!
    let memory = Memory()
    
    public init() {
        Database.setLogLevel(LogLevel.debug, domain: LogDomain.all)
        dictionaryRequestHandler = DictionaryRequestHandler()
        queryRequestHandler = QueryRequestHandler()
        databaseRequestHandler = DatabaseRequestHandler()
        documentRequestHandler = DocumentRequestHandler()
        replicatorRequestHandler = ReplicatorRequestHandler()
        dataTypesInitiatorHandler = DataTypesInitiatorHandler()
        server = GCDWebServer()
        server.addDefaultHandler(forMethod: "POST", request: GCDWebServerDataRequest.self) {
            (request) -> GCDWebServerResponse? in
            
            var rawArgs = [String: Any]()
            
            var method = ""
            
            if request.path.hasPrefix("/") {
                let start = request.path.index(request.path.startIndex, offsetBy: 1)
                method = request.path.substring(from: start)
            } else {
                method = request.path
            }
            
            do {
                let args = Args()
                var queryParams = request.query
                let r = request as! GCDWebServerDataRequest

                if queryParams?.count == 0 {
                    queryParams = r.jsonObject as? Dictionary<String, AnyObject>
                }

                if let queryParams = queryParams {
                    // Get args from query params
                    for param in queryParams {
                        rawArgs[param.key as! String] = param.value

                        let value: Any = ValueSerializer.deserialize(value:(param.value as! String), memory: self.memory)!
                        // Handle nil value
                        args.set(value: value, forName: param.key as! String)
                    }
                }

                // Find and invoke the method on the RequestHandler.
                var body: Any? = nil
                if "release" == method {
                    self.memory.remove(address: rawArgs["object"] as! String)
                } else {
                    var result: Any? = nil
                    if method.hasPrefix("query") {
                        result = try self.queryRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("database") {
                        result = try self.databaseRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("replicator") {
                        result = try self.replicatorRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("document") {
                        result = try self.documentRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("dictionary") {
                        result = try self.dictionaryRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("datatype") {
                        result = try self.dataTypesInitiatorHandler.handleRequest(method: method, args: args)
                    } else {
                        throw ServerError.MethodNotImplemented(method)
                    }
                    if result != nil {
                        body = ValueSerializer.serialize(value: result, memory: self.memory);
                    }
                }

                if body != nil {
                    return GCDWebServerDataResponse(text: body as! String)
                } else {
                    // Send 200 code and close
                    return GCDWebServerResponse(statusCode: 200)
                }
            } catch let error {
                // Send 400 error code
                let response = GCDWebServerDataResponse(text: error.localizedDescription)!
                response.statusCode = 400
                return response
            }
        }
        server.start(withPort: kPort, bonjourName: nil)
    }
}
