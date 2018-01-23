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
        } else if ((value as? NSNull) != nil) {
            return "null"
        } else if (value is String) {
            let string = value as? String
            return "\"" + string! + "\""
        } else if (value is Int){
            let number:Int = value as! Int
            return "I" + String(number)
        // Swift does not have a Long type
        } else if (value is Double){
            let number:Double = value as! Double
            return "D" + String(number)
        } else if (value is Float){
            let number:Float = value as! Float
            return "F" + String(number)
        } else if (value is NSNumber){
            let number:NSNumber = value as! NSNumber
            return "#" + "\(number)"
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
        print("value in deserialize is \(value)")
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
                print("map_param key is \(key)")
                if let key_value = deserialize(value: map_param.value as? String, memory: memory) as Any? {
                     map[key] = key_value
                }
                else{
                    map[key] = NSNull()
                }
                    print("map_param key value is ....\(map[key])")
            }
            print("Returned map in deserialize is ....\(map)")
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
                 let object: Any? = deserialize(value: string, memory: memory)
                 list.append(object ?? NSNull.init())
            }
            print("list in deserialize is \(list)")
            return list as? T
        } else {
            return "Invalid value type \(String(describing: value))" as? T
        }
    }
}
