//
//  DataTypesInitiatorHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/3/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class DataTypesInitiatorRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ///////////////////////////////
        // Initiates Complex Objects //
        ///////////////////////////////
        case "datatype_setArray":
            let arr:  [Any] = args.get(name: "name")!
            return arr
            
        case "datatype_hashMap":
            return Dictionary<String, Any>()
            
        case "datatype_get":
            let map: Dictionary<String, Any> = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return map[key]

        case "datatype_put":
            var map: Dictionary<String, Any> = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Any = args.get(name: "value")!
            map[key] = value
            
        case "datatype_setDate":
            return Date()
            
        case "datatype_setDouble":
            let obj: Double = args.get(name: "value")! as Double
            return obj
            
        case "datatype_setFloat":
            let obj: Float = args.get(name: "value")! as Float
            return obj
            
        // There is no Long type in Swift
            
        case "datatype_compare":
            let first: String = args.get(name: "first")!
            let second: String = args.get(name: "second")!
            
            if first == second {
                return true
            }
            
            return false
            
        case "datatype_compareHashMap":
            let first: Dictionary<String, Any> = args.get(name: "first")!
            let second: Dictionary<String, Any> = args.get(name: "second")!

            let firstKeys: Set<String> = Set(first.keys)
            let secondKeys: Set<String> = Set(second.keys)
        
            do {
                for key in secondKeys {
                    if !(first[key] as! String == second[key] as! String ) {
                        return false
                    }
                }

                for key in firstKeys {
                    if !second.keys.contains(key) {
                        return false
                    }
                }
            } catch {
                return false
            }
            return true

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DataTypesInitiatorRequestHandler.VOID
    }
}

