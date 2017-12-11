//
//  ValueSerializer.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/30/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

public class ValueSerializer {
    public static func serialize(value: Any?, memory: Memory) -> Any {
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
        } else if (value is Dictionary<String, Any>) {
            let map = value as! Dictionary<String, Any>
            var stringMap = [String: Any]()
            
            for (key, val) in map {
                let stringVal = serialize(value: val, memory: memory)
                stringMap[key] = stringVal
            }
            
            do {
                let data = try JSONSerialization.data(withJSONObject: stringMap, options: [])
                let json = String.init(data: data, encoding: .utf8) as Any
                return json
            } catch {
                return "Error converting Dict to json"
            }
        } else if (value is Array<Any>) {
            let list = value as! Array<Any>
            var stringList = [String]()
            
            for object in list {
                let stringVal: String = serialize(value: object, memory: memory) as! String
                stringList.append(stringVal)
            }
            
            do {
                let data = try JSONSerialization.data(withJSONObject: stringList, options: [])
                return String.init(data: data, encoding: .utf8) as Any
            } catch {
                return "Error converting Array to json"
            }
        }
        else {
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
        } else if (value!.hasPrefix("{")) {
            let data: Data = value!.data(using: String.Encoding.utf8)!
            var stringMap = [String: Any]()

            do {
                stringMap = try JSONSerialization.jsonObject(with: data, options: JSONSerialization.ReadingOptions.mutableContainers) as! Dictionary<String, Any>
            } catch {
                return nil
            }
            var map: Dictionary = [String: Any]()
            
            for map_param in stringMap {
                let key = map_param.key
                map[key] = deserialize(value: map_param.value as? String, memory: memory)!
            }
            return map as? T
        } else if (value!.hasPrefix("[")) {
            let data: Data = value!.data(using: String.Encoding.utf8)!
            var stringList = [String]()
            do {
                stringList = try JSONSerialization.jsonObject(with: data, options: JSONSerialization.ReadingOptions.mutableContainers) as! [String]
            } catch {
                return nil
            }
            var list = [Any]()
            
            for string in stringList {
                let object: Any = deserialize(value: string, memory: memory)!
                
                list.append(object);
            }
            
            return list as? T
        }
        else {
            if (value?.range(of:".")) != nil {
                return Double(value!) as? T
            } else {
                return Int(value!) as? T
            }
        }
    }
}
