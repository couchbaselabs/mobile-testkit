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
    case MethodNotFound
}

public class Server {
    let kPort:UInt = 8989
    let server: GCDWebServer!
    let requestHandler: RequestHandler!
    let memory = Memory()
    
    public init() {
        Database.setLogLevel(LogLevel.debug, domain: LogDomain.all)
        requestHandler = RequestHandler()
        server = GCDWebServer()
        server.addDefaultHandler(forMethod: "POST", request: GCDWebServerDataRequest.self) {
            (request) -> GCDWebServerResponse? in
            
            let rawArgs = request.query
            
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
                        let value: Any = ValueSerializer.deserialize(value:(param.value as! String), memory: self.memory)!
                        // Handle nil value
                        args.set(value: value, forName: param.key as! String)
                    }
                }

                // Find and invoke the method on the RequestHandler.
                var body: Any? = nil
                if "release" == method {
                    self.memory.remove(address: rawArgs!["object"] as! String)
                } else {
                    let result = try self.requestHandler.handleRequest(method: method, args: args)
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
