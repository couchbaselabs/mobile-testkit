//
//  SessionAuthenticatorRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/26/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class SessionAuthenticatorRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////////////////
        // SessionAuthenticator //
        //////////////////////////
        case "sessionauthenticator_create":
            let sessionid: String! = args.get(name: "sessionId")
            let cookiename: String! = args.get(name: "cookieName")
            return SessionAuthenticator(sessionID: sessionid, cookieName: cookiename)
            
        case "sessionauthenticator_getSessionId":
            let session: SessionAuthenticator = args.get(name: "session")!
            return session.sessionID

        case "sessionauthenticator_getCookieName":
            let session: SessionAuthenticator = args.get(name: "session")!
            return session.cookieName

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
