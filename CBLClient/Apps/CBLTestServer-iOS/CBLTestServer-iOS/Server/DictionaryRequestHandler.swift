//
//  RequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/31/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//
import Foundation
import CouchbaseLiteSwift


public class DictionaryRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        /////////////////////////////
        // MutableDictionaryObject //
        /////////////////////////////
        case "dictionary_create":
            let dictionary: [String: Any]? = args.get(name: "content_dict")!
            if dictionary != nil {
                return MutableDictionaryObject(data: dictionary)
            } else {
                return MutableDictionaryObject()
            }

        case "dictionary_toMutableDictionary":
            let dictionary: [String: Any]? = args.get(name: "dictionary")!
            return MutableDictionaryObject(data: dictionary)
            
        case "dictionary_count":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            return dictionary.count
            
        case "dictionary_getString":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.string(forKey: key)
        
        case "dictionary_setData":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let data: [String: Any]? = args.get(name: "data")!

            return dictionary.setData(data)
        
        case "dictionary_setString":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: String = args.get(name: "value")!
            
            return dictionary.setString(value, forKey: key)
            
        case "dictionary_getNumber":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.number(forKey: key)
        
        case "dictionary_setNumber":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: NSNumber = args.get(name: "value")!
            
            return dictionary.setNumber(value, forKey: key)
        
        case "dictionary_getInt":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.int(forKey: key)
        
        case "dictionary_getLong":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.int64(forKey: key)

        case "dictionary_setInt":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Int = args.get(name: "value")!
            
            return dictionary.setInt(value, forKey: key)
        
        case "dictionary_setLong":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Int64 = args.get(name: "value")! as Int64
            
            return dictionary.setInt64(value, forKey: key)
     
        case "dictionary_getFloat":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.float(forKey: key)
        
        case "dictionary_setFloat":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Float = args.get(name: "value")!
            
            return dictionary.setFloat(value, forKey: key)
        
        case "dictionary_getDouble":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.double(forKey: key)
        
        case "dictionary_setDouble":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Float = args.get(name: "value")!
            
            return dictionary.setDouble(Double(value), forKey: key)
        
        case "dictionary_getBoolean":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.boolean(forKey: key)
        
        case "dictionary_setBoolean":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Bool = args.get(name: "value")!
            
            return dictionary.setBoolean(value, forKey: key)
        
        case "dictionary_getBlob":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.blob(forKey: key)
        
        case "dictionary_setBlob":
            // let dictionary: [String: Any]? = args.get(name: "dictionary")!
            // let mutableDictionary = MutableDictionaryObject(data: dictionary)
            let mutableDictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Blob = args.get(name: "value")!
            
            return mutableDictionary.setBlob(value, forKey: key)
        
        case "dictionary_getDate":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let dict_date = dictionary.date(forKey: key)
            return dict_date
        
        case "dictionary_setDate":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Date = args.get(name: "value")!
            
            return dictionary.setDate(value, forKey: key)
        
        case "dictionary_getArray":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.array(forKey: key)
        
        case "dictionary_setArray":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: ArrayObject = args.get(name: "value")!
            
            return dictionary.setArray(value, forKey: key)

        case "dictionary_getValue":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.value(forKey: key)

        case "dictionary_setValue":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let value: Any? = args.get(name: "value")!
            let key: String = args.get(name: "key")!
            return dictionary.setValue(value, forKey: key)
            
        case "dictionary_getDictionary":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.dictionary(forKey: key)
        
        case "dictionary_setDictionary":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: DictionaryObject = args.get(name: "value")!
            
            return dictionary.setDictionary(value, forKey: key)
            
        case "dictionary_getKeys":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            return dictionary.keys

        case "dictionary_toMap":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            return dictionary.toDictionary()
        
        case "dictionary_remove":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.removeValue(forKey: key)
        
        case "dictionary_contains":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.contains(key)
        
        case "dictionary_iterator":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            return  dictionary.makeIterator()
        
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}

