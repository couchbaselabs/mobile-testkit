//
//  EncryptionKeyRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/26/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class EncryptionKeyRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ///////////////////
        // EncryptionKey //
        ///////////////////
        case "encryptionkey_create":
            let key: Data? = args.get(name: "key")!
            let password: String? = args.get(name: "password")!
            
            if (password != nil){
                return EncryptionKey.password(password!)
            } else if(key != nil){
                return EncryptionKey.key(key!)
            } else {
                throw RequestHandlerError.InvalidArgument("Encryption parameter is null")
            }

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
