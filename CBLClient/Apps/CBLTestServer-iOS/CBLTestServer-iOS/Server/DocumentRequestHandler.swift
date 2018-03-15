//
//  DocumentRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//
import Foundation
import CouchbaseLiteSwift


public class DocumentRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////
        // Document //
        //////////////
        case "document_create":
            let id: String? = (args.get(name: "id"))
            let dictionary: [String: Any]? = (args.get(name: "dictionary"))

            if id != nil {
                if dictionary == nil {
                    return MutableDocument(id: id)
                } else {
                    return MutableDocument(id: id, data: dictionary)
                }
            } else {
                if dictionary == nil {
                    let doc = MutableDocument()
                    print("doc is \(doc)")
                    return doc
                } else {
                    return MutableDocument(data: dictionary)
                }
            }
            
        case "document_toMutable":
            let document: Document = args.get(name:"document")!
            return document.toMutable()

        case "document_setValue":
            let document: MutableDocument = args.get(name:"document")!
            let value: Any? = args.get(name:"value")!
            let key: String = args.get(name:"key")!
            
            return document.setValue(value, forKey: key)
           
        case "document_getString":
            let document: Document = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return document.string(forKey: key)

        case "document_setString":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: String = (args.get(name: "value"))!
            
            document.setString(value, forKey: key)

        case "document_getNumber":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return document.number(forKey: key)

        case "document_setNumber":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: NSNumber = (args.get(name: "value"))!
            
            return document.setNumber(value, forKey: key)

        case "document_getInt":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return  document.int(forKey: key)

        case "document_setInt":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Int = (args.get(name: "value"))!
            
            return  document.setInt(value, forKey: key)

        case "document_getLong":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return  document.int64(forKey: key)

        case "document_setLong":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Int64 = (args.get(name: "value"))!
            
            return  document.setInt64(value, forKey: key)

        case "document_getFloat":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return  document.float(forKey: key)

        case "document_setFloat":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Float = (args.get(name: "value"))!

            return  document.setFloat(value, forKey: key)
        
        case "document_getDouble":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return  document.double(forKey: key)

        case "document_setDouble":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Float = (args.get(name: "value"))!
            let double_value = Double(value)
            return  document.setDouble(double_value, forKey: key)

        case "document_getBoolean":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return  document.boolean(forKey: key)

        case "document_setBoolean":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Bool = (args.get(name: "value"))!
            return  document.setBoolean(value, forKey: key)
        
        case "document_getBlob":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return document.blob(forKey: key)

        case "document_setBlob":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Blob = (args.get(name: "value"))!
            return  document.setBlob(value, forKey: key)
        
        case "document_getDate":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return document.date(forKey: key)
        
        case "document_setDate":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: Date = (args.get(name: "value"))!
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ssZ"

            return document.setDate(value, forKey: key)
        
        case "document_getArray":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return  document.array(forKey: key)

        case "document_setArray":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: ArrayObject = (args.get(name: "value"))!
            return  document.setArray(value, forKey: key)

        case "document_getDictionary":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return  document.dictionary(forKey: key)

        case "document_setDictionary":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            let value: DictionaryObject = (args.get(name: "value"))!
            return  document.setDictionary(value, forKey: key)
            
        case "document_setData":
            let document: MutableDocument = (args.get(name: "document"))!
            let data: Dictionary<String, Any> = (args.get(name: "data"))!

            return  document.setData(data)

        case "document_getKeys":
            let document: MutableDocument = (args.get(name: "document"))!
            
            return document.keys
        
        case "document_getValue":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!

            return document.value(forKey: key)

        case "document_removeKey":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return  document.removeValue(forKey: key)

        case "document_delete":
            let database: Database = (args.get(name:"database"))!
            let document: MutableDocument = args.get(name:"document")!
            
            try! database.deleteDocument(document)
            
        case "document_getId":
            let document: Document = args.get(name: "document")!
            
            return document.id

        case "document_count":
            let document: MutableDocument = (args.get(name: "document"))!
            
            return document.count

        case "document_contains":
            let document: MutableDocument = (args.get(name: "document"))!
            let key: String = (args.get(name: "key"))!
            
            return document.contains(key: key)

        case "document_toMap":
            let document: MutableDocument = (args.get(name: "document"))!
            
            return document.toDictionary()

        case "document_getIterator":
            let document: MutableDocument = (args.get(name: "document"))!
            
            return document.makeIterator()
            
        case "document_isEqual":
            let document1: MutableDocument = (args.get(name: "document1"))!
            let document2: MutableDocument = (args.get(name: "document2"))!
            
            return document1 == document2

        case "document_getHash":
            let document: MutableDocument = (args.get(name: "document"))!
            
            return document.hashValue

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DocumentRequestHandler.VOID
    }
}

class MyDocumentChangeListener  {
    var changes: [DocumentChange] = []
    
    lazy var listener: (DocumentChange) -> Void = { (change: DocumentChange) in
        self.changes.append(change)
    }
    
    public func getChanges() -> [DocumentChange] {
        return changes
    }
}
