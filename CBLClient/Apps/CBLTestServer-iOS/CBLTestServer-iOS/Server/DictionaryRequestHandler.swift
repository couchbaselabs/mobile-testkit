//
//  RequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/31/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift
import CouchbaseLiteSwift.CBLDictionary_Swift

enum DictionaryRequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class DictionaryRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ///////////////////////
        // MutableDictionary //
        ///////////////////////
        case "dictionary_create":
            let dictionary: [String: Any]? = args.get(name: "content_dict")!
            if dictionary != nil {
                return MutableDictionaryObject(withData: dictionary)
            } else {
                return MutableDictionaryObject()
            }
            
        case "dictionary_count":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            return dictionary.count
            
        case "dictionary_getString":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.string(forKey: key)
        
        case "dictionary_setString":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: String = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
            
        case "dictionary_getNumber":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.number(forKey: key)
        
        case "dictionary_setNumber":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: NSNumber = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getInt":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.int(forKey: key)
        
        case "dictionary_getInt64":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.int64(forKey: key)

        case "dictionary_setInt":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Int = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_setInt64":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Int64 = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
     
        case "dictionary_getFloat":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.float(forKey: key)
        
        case "dictionary_setFloat":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Float = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getDouble":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.double(forKey: key)
        
        case "dictionary_setDouble":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Double = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getBoolean":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.boolean(forKey: key)
        
        case "dictionary_setBoolean":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Bool = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getBlob":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.blob(forKey: key)
        
        case "dictionary_setBlob":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Blob = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getDate":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.date(forKey: key)
        
        case "dictionary_setDate":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: Date = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
        
        case "dictionary_getArray":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.array(forKey: key)
        
        case "setArray":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: ArrayObject = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)

        case "dictionary_getValue":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.value(forKey: key)

        case "dictionary_setValue":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let value: Any? = args.get(name: "value")!
            let key: String = args.get(name: "key")!
            return dictionary.setValue(value, forKey: key)
            
        case "dictionary_getDictionary":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.dictionary(forKey: key)
        
        case "dictionary_setDictionary":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let value: DictionaryObject = args.get(name: "value")!
            
            return dictionary.setValue(value, forKey: key)
            
        case "dictionary_getKeys":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            return dictionary.keys

        case "dictionary_toDictionary":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            return dictionary.toDictionary()
        
        case "dictionary_remove":
            let dictionary: MutableDictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.removeValue(forKey: key)
        
        case "dictionary_contains":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            return dictionary.contains(key)
        
        case "dictionary_iterator":
            let dictionary: DictionaryObject = args.get(name: "dictionary")!
            return  dictionary.makeIterator()

            
        default:
            throw DictionaryRequestHandlerError.MethodNotFound(method)
        }
        return DictionaryRequestHandler.VOID;
    }
}






