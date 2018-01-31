//
//  ArrayRequesthandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/26/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class ArrayRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ////////////////////////
        // MutableArrayObject //
        ////////////////////////
        case "array_create":
            let array: [Any]? = args.get(name: "content_array")!
            if array != nil {
                return MutableArrayObject(data: array)
            } else {
                return MutableArrayObject()
            }

        case "array_count":
            let array: MutableArrayObject = args.get(name: "array")!
            return array.count

        case "array_getString":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.string(at: index)
            
        case "array_setData":
            let array: MutableArrayObject = args.get(name: "array")!
            let data: [Any]? = args.get(name: "data")!
            
            return array.setData(data)
            
        case "array_setString":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: String = args.get(name: "value")!
            
            return array.setString(value, at: index)
            
        case "array_getNumber":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.number(at: index)
            
        case "array_setNumber":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: NSNumber = args.get(name: "value")!
            
            return array.setNumber(value, at: index)
            
        case "array_getInt":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.int(at: index)
            
        case "array_getInt64":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.int64(at: index)
            
        case "array_setInt":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Int = args.get(name: "value")!
            
            return array.setInt(value, at: index)
            
        case "array_setInt64":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Int64 = args.get(name: "value")!
            
            return array.setInt64(value, at: index)
            
        case "array_getFloat":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.float(at: index)
            
        case "array_setFloat":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Float = args.get(name: "value")!
            
            return array.setFloat(value, at: index)
            
        case "array_getDouble":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.double(at: index)
            
        case "array_setDouble":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Double = args.get(name: "value")!
            
            return array.setDouble(value, at: index)
            
        case "array_getBoolean":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.boolean(at: index)
            
        case "array_setBoolean":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Bool = args.get(name: "value")!
            
            return array.setBoolean(value, at: index)
            
        case "array_getBlob":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.blob(at: index)
            
        case "array_setBlob":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Blob = args.get(name: "value")!
            
            return array.setBlob(value, at: index)
            
        case "array_getDate":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.date(at: index)
            
        case "array_setDate":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: Date = args.get(name: "value")!
            
            return array.setDate(value, at: index)
            
        case "array_getArray":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.array(at: index)
            
        case "array_setArray":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            let value: ArrayObject = args.get(name: "value")!
            
            return array.setArray(value, at: index)
            
        case "array_getValue":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.value(at: index)
            
        case "array_setValue":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Any? = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            return array.setValue(value, at: index)
            
        case "array_getDictionary":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.array(at: index)
            
        case "array_setDictionary":
            let array: MutableArrayObject = args.get(name: "array")!
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let index: Int = args.get(name: "key")!
            
            return array.setDictionary(dictionary, at: index)
           
        case "array_toArray":
            let array: MutableArrayObject = args.get(name: "array")!
            return array.toArray()
            
        case "array_removeValue":
            let array: MutableArrayObject = args.get(name: "array")!
            let index: Int = args.get(name: "key")!
            return array.removeValue(at: index)
           
        case "array_iterator":
            let array: MutableArrayObject = args.get(name: "array")!
            return  array.makeIterator()

        case "array_getIterator":
            let array: MutableArrayObject = args.get(name: "array")!
            
            return array.makeIterator()
            
        case "array_isEqual":
            let array1: MutableArrayObject = args.get(name: "array1")!
            let array2: MutableArrayObject = args.get(name: "array2")!
            
            return array1 == array2
            
        case "array_getHash":
            let array: MutableArrayObject = args.get(name: "array")!
            
            return array.hashValue
           
        case "array_addValue":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Any? = args.get(name: "value")!

            return array.addValue(value)

        case "array_addString":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: String = args.get(name: "value")!
            
            return array.addString(value)

        case "array_addNumber":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: NSNumber? = args.get(name: "value")!
            
            return array.addNumber(value)

        case "array_addInt":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Int = args.get(name: "value")!
            
            return array.addInt(value)

        case "array_addInt64":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Int64 = args.get(name: "value")!
            
            return array.addInt64(value)

        case "array_addFloat":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Float = args.get(name: "value")!
            
            return array.addFloat(value)

        case "array_addDouble":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Double = args.get(name: "value")!
            
            return array.addDouble(value)

        case "array_addBlob":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Blob = args.get(name: "value")!
            
            return array.addBlob(value)

        case "array_addBoolean":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Bool = args.get(name: "value")!
            
            return array.addBoolean(value)

        case "array_addDate":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Date = args.get(name: "value")!
            
            return array.addDate(value)

        case "array_addArray":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: ArrayObject = args.get(name: "value")!
            
            return array.addArray(value)

        case "array_addDictionary":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: DictionaryObject = args.get(name: "value")!
            
            return array.addDictionary(value)
            
        case "array_insertValue":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Any? = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertValue(value, at: index)
            
        case "array_insertString":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: String = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertString(value, at: index)
            
        case "array_insertNumber":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: NSNumber? = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertNumber(value, at: index)
            
        case "array_insertInt":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Int = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertInt(value, at: index)
            
        case "array_insertInt64":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Int64 = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertInt64(value, at: index)
            
        case "array_insertFloat":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Float = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertFloat(value, at: index)
            
        case "array_insertDouble":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Double = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertDouble(value, at: index)
            
        case "array_insertBlob":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Blob = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertBlob(value, at: index)
            
        case "array_insertBoolean":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Bool = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertBoolean(value, at: index)
            
        case "array_insertDate":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: Date = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertDate(value, at: index)
            
        case "array_insertArray":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: ArrayObject = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertArray(value, at: index)
            
        case "array_insertDictionary":
            let array: MutableArrayObject = args.get(name: "array")!
            let value: DictionaryObject = args.get(name: "value")!
            let index: Int = args.get(name: "key")!
            
            return array.insertDictionary(value, at: index)
            
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
