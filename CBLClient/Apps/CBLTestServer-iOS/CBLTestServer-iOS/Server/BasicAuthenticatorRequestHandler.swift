//
//  BasicAuthenticatorRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class BasicAuthenticatorRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ////////////////////////
        // BasicAuthenticator //
        ////////////////////////
        case "basicAuthenticator_create":
            let username: String = args.get(name: "username")!
            let password: String = args.get(name: "password")!
            return BasicAuthenticator(username: username, password: password)
            
        case "basicAuthenticator_getPassword":
            let authenticator: BasicAuthenticator = args.get(name: "authenticator")!
            return authenticator.password
        
        case "basicAuthenticator_getUsername":
            let authenticator: BasicAuthenticator = args.get(name: "authenticator")!
            return authenticator.username

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return BasicAuthenticatorRequestHandler.VOID
    }
}
