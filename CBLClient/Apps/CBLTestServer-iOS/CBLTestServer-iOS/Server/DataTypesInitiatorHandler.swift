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
            let formatter = DateFormatter()
            formatter.dateFormat = "y-MM-dd H:m:ss.SSSS"
            let date = Date()
            let date_string = formatter.string(from: date)
            print("datatype_setDate date_string: \(date_string)")
            return date_string
            
            
        case "datatype_setDouble":
            let float_obj: Float = args.get(name: "value")!
            return Double(float_obj)
           
        case "datatype_setFloat":
            let obj: Float = args.get(name: "value")! as Float
            return obj
            
        case "datatype_setLong":
            // There is no Long type in Swift
            let obj: Int64 = args.get(name: "value")! as Int64
            return obj
            
        case "datatype_compare":
            let first: String = args.get(name: "first")!
            let second: String = args.get(name: "second")!
            
            if first == second {
                return true
            }
            
            return false
        
        case "datatype_compareDate":
            let date1: String = args.get(name: "date1")!
            let date2: Date = args.get(name: "date2")!
            
            print("date1: \(date1)")
            print("date2: \(date2)")
            let formatter = DateFormatter()
            formatter.dateFormat = "y-MM-dd H:m:ss.SSSS"

            if formatter.date(from: date1) == date2 {
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

        case "datatype_compareLong":
            let long1: Int = args.get(name: "long1")!
            let long2: Int = args.get(name: "long2")!
            
            if Int64(long1) == Int64(long2) {
                return true
            } else {
                return false
            }
    
        case "datatype_compareHashMap":
            let first: Dictionary<String, Any> = args.get(name: "first")!
            let second: Dictionary<String, Any> = args.get(name: "second")!
            
            print("first is \(first)")
            print("second is \(second)")
            
            return NSDictionary(dictionary: first).isEqual(to: second)
            
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

