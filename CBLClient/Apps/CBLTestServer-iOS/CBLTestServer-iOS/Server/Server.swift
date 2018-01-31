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
    case IOException(String)
}

public class Server {
    let kPort:UInt = 8080
    let server: GCDWebServer!
    let dictionaryRequestHandler: DictionaryRequestHandler!
    let queryRequestHandler: QueryRequestHandler!
    let databaseRequestHandler: DatabaseRequestHandler!
    let documentRequestHandler: DocumentRequestHandler!
    let replicatorRequestHandler: ReplicatorRequestHandler!
    let arrayRequestHandler: ArrayRequestHandler!
    let sessionauthenticatorRequestHandler: SessionAuthenticatorRequestHandler!
    let encryptionkeyRequestHandler: EncryptionKeyRequestHandler!
    let conflictRequestHandler: ConflictRequestHandler!
    let blobRequestHandler: BlobRequestHandler!
    let datatypeRequestHandler: DataTypesInitiatorRequestHandler!
    let replicatorConfigurationRequestHandler: ReplicatorConfigurationRequestHandler!
    let expressionRequestHandler: ExpressionRequestHandler!
    let collationRequestHandler: CollationRequestHandler!
    let dataSourceRequestHandler: DataSourceRequestHandler!
    let functionRequestHandler: FunctionRequestHandler!
    let selectResultRequestHandler: SelectResultRequestHandler!
    let resultRequestHandler: ResultRequestHandler!
    let basicAuthenticatorRequestHandler: BasicAuthenticatorRequestHandler!
    let databaseConfigurationRequestHandler: DatabaseConfigurationRequestHandler!
    let memory = Memory()
    
    public init() {
        Database.setLogLevel(LogLevel.debug, domain: LogDomain.all)
        dictionaryRequestHandler = DictionaryRequestHandler()
        queryRequestHandler = QueryRequestHandler()
        databaseRequestHandler = DatabaseRequestHandler()
        documentRequestHandler = DocumentRequestHandler()
        replicatorRequestHandler = ReplicatorRequestHandler()
        arrayRequestHandler = ArrayRequestHandler()
        sessionauthenticatorRequestHandler = SessionAuthenticatorRequestHandler()
        encryptionkeyRequestHandler = EncryptionKeyRequestHandler()
        conflictRequestHandler = ConflictRequestHandler()
        blobRequestHandler = BlobRequestHandler()
        datatypeRequestHandler = DataTypesInitiatorRequestHandler()
        replicatorConfigurationRequestHandler = ReplicatorConfigurationRequestHandler()
        expressionRequestHandler = ExpressionRequestHandler()
        collationRequestHandler = CollationRequestHandler()
        dataSourceRequestHandler = DataSourceRequestHandler()
        functionRequestHandler = FunctionRequestHandler()
        selectResultRequestHandler = SelectResultRequestHandler()
        resultRequestHandler = ResultRequestHandler()
        basicAuthenticatorRequestHandler = BasicAuthenticatorRequestHandler()
        databaseConfigurationRequestHandler = DatabaseConfigurationRequestHandler()
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

                        if let value = ValueSerializer.deserialize(value:(param.value as? String), memory: self.memory) as Any? {
                            // Handle nil value
                            args.set(value: value, forName: param.key as! String)
                        } else {
                            args.set(value: "", forName: param.key as! String)
                        }
                        print("param and value is \(param.key) and value is \(param.value)")
                    }
                }

                // Find and invoke the method on the RequestHandler.
                var body: Any? = nil
                if "release" == method {
                    self.memory.remove(address: rawArgs["object"] as! String)
                } else if "flushMemory" == method {
                    self.memory.flushMemory()
                } else{
                    var result: Any? = nil
                    if method.hasPrefix("query") {
                        result = try self.queryRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("databaseConfiguration") {
                        result = try self.databaseConfigurationRequestHandler.handleRequest(method: method, args: args)
                    }else if method.hasPrefix("database") {
                        result = try self.databaseRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("document") {
                        result = try self.documentRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("dictionary") {
                        result = try self.dictionaryRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("array") {
                        result = try self.arrayRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("sessionAuthenticator") {
                        result = try self.sessionauthenticatorRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("encryptionkey") {
                        result = try self.encryptionkeyRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("conflict") {
                        result = try self.conflictRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("blob") {
                        result = try self.blobRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("datatype") {
                        result = try self.datatypeRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("replicatorConfiguration") {
                        result = try self.replicatorConfigurationRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("replicator") {
                        result = try self.replicatorRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("expression") {
                        result = try self.expressionRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("collation") {
                        result = try self.collationRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("dataSource") {
                        result = try self.dataSourceRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("function") {
                        result = try self.functionRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("selectResult") {
                        result = try self.selectResultRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("result") {
                        result = try self.resultRequestHandler.handleRequest(method: method, args: args)
                    } else if method.hasPrefix("basicAuthenticator") {
                        result = try self.basicAuthenticatorRequestHandler.handleRequest(method: method, args: args)
                    } else {
                        throw ServerError.MethodNotImplemented(method)
                    }
                    if result != nil {
                        print("result is \(result)")
                        body = ValueSerializer.serialize(value: result, memory: self.memory);
                    }
                }

                if body != nil {
                    return GCDWebServerDataResponse(text: body as! String)
                } else {
                    // Send 200 code and close
                    return GCDWebServerDataResponse(text: "I-1")
                }
            } catch let error as NSError {
                // Send 400 error code
                let response = GCDWebServerDataResponse(text: error.localizedDescription)!
                print("Error is : \(error.localizedDescription)")
                response.statusCode = error.code as Int
                return response
            }
        }
        server.start(withPort: kPort, bonjourName: nil)
    }
}
