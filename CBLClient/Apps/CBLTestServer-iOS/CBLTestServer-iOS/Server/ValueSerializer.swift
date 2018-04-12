//
//  ValueSerializer.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/30/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation

public class ValueSerializer {

    public static func serialize(value: Any?, memory: Memory) throws -> Any {
        guard let v = value else {
            return "null"
        }
        
        if ((v as? NSNull) != nil) {
            return "null"
        } else if (v is String) {
            let string = v as! String
            return "\"" + string + "\""
        } else if (v is Int){
            let number = v as! Int
            return "I" + String(number)
            // Swift does not have a Long type
        } else if (v is Double){
            let number = v as! Double
            return "D" + String(number)
        } else if (v is Float){
            let number = v as! Float
            return "F" + String(number)
        } else if (v is NSNumber){
            let number = v as! NSNumber
            return "#" + "\(number)"
        } else if (v is Bool) {
            let bool = v as! Bool
            return (bool ? "true" : "false")
        } else if (v is Dictionary<String, Any>) {
            let map = v as! Dictionary<String, Any>
            var stringMap = [String: Any]()
            
            for (key, val) in map {
                let stringVal = try serialize(value: val, memory: memory)
                stringMap[key] = stringVal
            }
            
            do {
                let data = try JSONSerialization.data(withJSONObject: stringMap, options: [])
                let json = String.init(data: data, encoding: .utf8) as Any
                return json
            } catch {
                throw ValueSerializerError.SerializerError("Error converting Dict to json")
            }
        } else if (v is Array<Any>) {
            let list = v as! Array<Any>
            var stringList = [String]()
            
            for object in list {
                let stringVal: String = try serialize(value: object, memory: memory) as! String
                stringList.append(stringVal)
            }
            
            do {
                let data = try JSONSerialization.data(withJSONObject: stringList, options: [])
                return String.init(data: data, encoding: .utf8) as Any
            } catch {
                throw ValueSerializerError.SerializerError("Error converting Array to json")
            }
        }
        else {
            return memory.add(value: value!)
        }
    }
    
    public static func deserialize<T>(value: String?, memory: Memory) throws -> T? {
        if value == nil || value == "null" {
            return nil
        } else if (value!.hasPrefix("@")) {
            return memory.get(address:value!)
        } else if (value!.hasPrefix("\"") && value!.hasSuffix("\"")) {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: -1)
            let range = start..<end
            return value!.substring(with: range) as? T
        } else if value!.hasPrefix("I") {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: 0)
            let range = start..<end
            return Int(value!.substring(with: range)) as? T
            
        } else if value!.hasPrefix("F") {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: 0)
            let range = start..<end
            return Float(value!.substring(with: range)) as? T
           
        } else if value!.hasPrefix("D") {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: 0)
            let range = start..<end
            return Double(value!.substring(with: range)) as? T
        } else if value!.hasPrefix("L") {
            let start = value!.index(value!.startIndex, offsetBy: 1)
            let end = value!.index(value!.endIndex, offsetBy: 0)
            let range = start..<end
            return Int64(value!.substring(with: range)) as? T
        } else if value!.hasPrefix("#") {
                if (value?.range(of:".")) != nil {
                    return Double(value!) as? T
                } else {
                    return Int(value!) as? T
                }
        } else if (value == "true") {
            return true as? T
        } else if (value == "false") {
            return false as? T
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
                if let key_value = try deserialize(value: map_param.value as? String, memory: memory) as Any? {
                     map[key] = key_value
                }
                else{
                    map[key] = NSNull()
                }
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
                 let object: Any? = try deserialize(value: string, memory: memory)
                 list.append(object ?? NSNull.init())
            }
            return list as? T
        } else {
            throw ValueSerializerError.DeSerializerError("Invalid value type \(String(describing: value))")
        }
    }
}
