//
//  DataTypesInitiatorHandler.swift
//  CBLTestServer-iOS
//
<<<<<<< HEAD
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class DataTypesInitiatorHandler {
    public static let VOID = NSObject()
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DataTypesInitiatorHandler.VOID
    }
}
=======
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
            let float_obj: Float = args.get(name: "value")!
            return Double(float_obj)
           
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
        
        case "datatype_compareDate":
            let date1: Date = args.get(name: "date1")!
            let date2: Date = args.get(name: "date2")!
            
            let formatter = DateFormatter()
            formatter.dateFormat = "y-MM-dd H:m:ss.SSSS"

            if formatter.string(from: date1) == formatter.string(from: date2) {
                return true
            } else {
                return false
            }

        case "datatype_compareDouble":
            let double1: Float = args.get(name: "double1")!
            let double2: Float = args.get(name: "double2")!
            
            if Double(double1) == Double(double2) {
                return true
            } else {
                return false
            }

        case "datatype_compareHashMap":
            let dict1: DictionaryObject = args.get(name: "dict1")!
            let dict2: DictionaryObject = args.get(name: "dict2")!
            
            if dict1 == dict2 {
                return true
            } else {
                return false
            }
            
        case "datatype_compareHashMap_org":
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

>>>>>>> refs/remotes/origin/feature/cbl20-query
