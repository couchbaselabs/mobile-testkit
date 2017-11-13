//
//  ValueSerializer.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/30/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

public class ValueSerializer {
    public static func serialize(value: Any?, memory: Memory) -> String {
        if value == nil {
            return "null"
        } else if (value is String) {
            let string = value as? String
            return "\"" + string! + "\""
        } else if (value is Int){
            let number:Int = value as! Int
            return String(number)
        } else if (value is UInt64){
            let number:UInt64 = value as! UInt64
            return String(number)
        } else if (value is Bool) {
            let bool:Bool = value as! Bool
            return (bool ? "true" : "false")
        } else {
            return memory.add(value: value!)
        }
    }
    
    public static func deserialize<T>(value: String?, memory: Memory) -> T? {
        if value == nil {
            return "null" as? T
        } else if (value!.hasPrefix("@")) {
            return memory.get(address:value!)
        } else if (value == "true") {
            return true as? T
        } else if (value == "false") {
            return false as? T
        } else if (value!.hasPrefix("\"") && value!.hasSuffix("\"")) {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: -1)
            let range = start..<end
            return value!.substring(with: range) as? T
        } else {
            if (value?.range(of:".")) != nil {
                return Double(value!) as? T
            } else {
                return Int(value!) as? T
            }
        }
    }
}
