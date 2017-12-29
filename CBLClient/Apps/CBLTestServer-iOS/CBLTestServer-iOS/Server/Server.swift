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
<<<<<<< HEAD
=======
    case IOException(String)
>>>>>>> refs/remotes/origin/feature/cbl20-query
}

public class Server {
    let kPort:UInt = 8989
    let server: GCDWebServer!
    let dictionaryRequestHandler: DictionaryRequestHandler!
    let queryRequestHandler: QueryRequestHandler!
    let databaseRequestHandler: DatabaseRequestHandler!
    let documentRequestHandler: DocumentRequestHandler!
    let replicatorRequestHandler: ReplicatorRequestHandler!
<<<<<<< HEAD
    let dataTypesInitiatorHandler: DataTypesInitiatorHandler!
=======
    let arrayRequestHandler: ArrayRequestHandler!
    let sessionauthenticatorRequestHandler: SessionAuthenticatorRequestHandler!
    let encryptionkeyRequestHandler: EncryptionKeyRequestHandler!
    let conflictRequestHandler: ConflictRequestHandler!
    let blobRequestHandler: BlobRequestHandler!
>>>>>>> refs/remotes/origin/feature/cbl20-query
    let memory = Memory()
    
    public init() {
        Database.setLogLevel(LogLevel.debug, domain: LogDomain.all)
        dictionaryRequestHandler = DictionaryRequestHandler()
        queryRequestHandler = QueryRequestHandler()
        databaseRequestHandler = DatabaseRequestHandler()
        documentRequestHandler = DocumentRequestHandler()
        replicatorRequestHandler = ReplicatorRequestHandler()
<<<<<<< HEAD
        dataTypesInitiatorHandler = DataTypesInitiatorHandler()
=======
        arrayRequestHandler = ArrayRequestHandler()
        sessionauthenticatorRequestHandler = SessionAuthenticatorRequestHandler()
        encryptionkeyRequestHandler = EncryptionKeyRequestHandler()
        conflictRequestHandler = ConflictRequestHandler()
        blobRequestHandler = BlobRequestHandler()
>>>>>>> refs/remotes/origin/feature/cbl20-query
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

<<<<<<< HEAD
                        let value: Any = ValueSerializer.deserialize(value:(param.value as! String), memory: self.memory)!
=======
                        let value: Any = ValueSerializer.deserialize(value:(param.value as? String), memory: self.memory)!
>>>>>>> refs/remotes/origin/feature/cbl20-query
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
<<<<<<< HEAD
                    } else if method.hasPrefix("datatype") {
                        result = try self.dataTypesInitiatorHandler.handleRequest(method: method, args: args)
=======
                    } else if method.hasPrefix("array") {
                        result = try self.arrayRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("sessionauthenticator") {
                        result = try self.sessionauthenticatorRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("encryptionkey") {
                        result = try self.encryptionkeyRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("conflict") {
                        result = try self.conflictRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("blob") {
                        result = try self.blobRequestHandler.handleRequest(method: method, args: args)
>>>>>>> refs/remotes/origin/feature/cbl20-query
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
