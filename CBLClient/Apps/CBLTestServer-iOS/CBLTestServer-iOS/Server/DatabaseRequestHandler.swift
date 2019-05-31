//
//  DatabaseRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class DatabaseRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {

        //////////////
        // Database //
        //////////////
    
        case "database_create":
            let name: String! = args.get(name: "name")
            let dbConfig: DatabaseConfiguration? = args.get(name: "config")
            do {
                if dbConfig != nil {
                    return try Database(name: name!, config: dbConfig!)
                } else {
                    return try Database(name: name!)
                }
            } catch {
                return error.localizedDescription
            }
            
        case "database_close":
            let database: Database = args.get(name:"database")!
            try database.close()

        case "database_getPath":
            let database: Database = (args.get(name:"database"))!

            return database.path

        case "database_delete":
            let database: Database = (args.get(name:"database"))!
            let document: Document = (args.get(name:"document"))!

            do {
                try database.deleteDocument(document)
            } catch {
                return error
            }
            
        case "database_deleteBulkDocs":
            let database: Database = args.get(name:"database")!
            let doc_ids: Array<String> = args.get(name: "doc_ids")!

            try database.inBatch {
                for id in doc_ids {
                    let document: Document = database.document(withID: id)!
                    do {
                        try! database.deleteDocument(document)
                    }
                }
            }

        case "database_deleteDB":
            let database: Database = args.get(name:"database")!
            
            try database.delete()

        case "database_exists":
            let name: String = args.get(name:"name")!
            let directory: String? = args.get(name:"directory")!
            return Database.exists(withName: name, inDirectory: directory)

        case "database_deleteIndex":
            let database: Database = (args.get(name:"database"))!
            let name: String = (args.get(name: "name"))!
            
            try database.deleteIndex(forName: name)

        case "database_getName":
            let database: Database = args.get(name:"database")!

            return database.name

        case "database_getDocument":
            let database: Database = (args.get(name:"database"))!
            let id: String? = args.get(name: "id")
            return database.document(withID: id!)
            
        case "database_save":
            let database: Database = (args.get(name:"database"))!
            let document: MutableDocument = args.get(name:"document")!
            try! database.saveDocument(document)
            
        case "database_saveWithConcurrency":
            let database: Database = (args.get(name:"database"))!
            let document: MutableDocument = args.get(name:"document")!
            let concurrencyControlType : String? = args.get(name:"concurrencyControlType")!
            var concurrencyType = ConcurrencyControl.lastWriteWins
            
            if let type = concurrencyControlType {
                if type == "failOnConflict" {
                    concurrencyType = .failOnConflict
                } else {
                    concurrencyType = .lastWriteWins
                }
            }
            try! database.saveDocument(document, concurrencyControl: concurrencyType)

        case "database_deleteWithConcurrency":
            let database: Database = (args.get(name:"database"))!
            let document: Document = (args.get(name:"document"))!
            let concurrencyControlType : String? = args.get(name:"concurrencyControlType")!
            var concurrencyType = ConcurrencyControl.lastWriteWins
            
            if let type = concurrencyControlType {
                if type == "failOnConflict" {
                    concurrencyType = .failOnConflict
                } else {
                    concurrencyType = .lastWriteWins
                }
            }
            do {
                try database.deleteDocument(document, concurrencyControl: concurrencyType)
            } catch {
                return error
            }

            
        case "database_purge":
            let database: Database = (args.get(name:"database"))!
            let document: MutableDocument = args.get(name:"document")!
            try! database.purgeDocument(document)
            
        case "database_contains":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!

            return database.document(withID: id) != nil

        case "database_getCount":
            let database: Database = (args.get(name:"database"))!
            return database.count

        case "database_compact":
            let database: Database = (args.get(name:"database"))!
            return try! database.compact()
            
        case "database_addChangeListener":
            let database: Database = (args.get(name:"database"))!
            var token: ListenerToken? = nil
            let docId: String? = (args.get(name:"docId"))
            if (docId != nil) {
                let changeListener = MyDocumentChangeListener()
                token = database.addDocumentChangeListener(withID: docId!, listener: changeListener.listener)
            } else {
                let changeListener = MyDatabaseChangeListener()
                token = database.addChangeListener(changeListener.listener)
            }
            
            return token

        case "database_removeChangeListener":
            let database: Database = (args.get(name:"database"))!
            let changeListener: ListenerToken = (args.get(name: "changeListener"))!

            database.removeChangeListener(withToken: changeListener)

        case "database_databaseChangeListenerChangesCount":
            let changeListener: MyDatabaseChangeListener = (args.get(name: "changeListener"))!

            return changeListener.getChanges().count

        case "database_databaseChangeListenerGetChange":
            let changeListener: MyDatabaseChangeListener = (args.get(name: "changeListener"))!
            let index: Int = (args.get(name: "index"))!

            return changeListener.getChanges()[index]

        case "database_databaseChangeListenerGetChanges":
            let changeListener: MyDatabaseChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges()
            
        case "database_databaseChangeGetDocumentId":
            let change: DatabaseChange = (args.get(name: "change"))!

            return change.documentIDs
            
        case "database_deleteDBbyName":
            let name: String = args.get(name:"name")!
            let directory: String? = args.get(name:"directory")!
            if let directory = directory {
                return try Database.delete(withName: name, inDirectory: directory)
            } else {
                return try Database.delete(withName: name)
            }

        case "database_saveDocuments":
            let database: Database = args.get(name:"database")!
            let documents: Dictionary<String, Dictionary<String, Any>> = args.get(name: "documents")!
            try database.inBatch {
                for doc in documents {
                    let id = doc.key
                    let data: Dictionary<String, Any> = doc.value
                    let document = MutableDocument(id: id, data: data)
                    try! database.saveDocument(document)
                    
                }
            }
 
        case "database_updateDocuments":
            let database: Database = args.get(name:"database")!
            let documents: Dictionary<String, Dictionary<String, Any>> = args.get(name: "documents")!
            try database.inBatch {
                for doc in documents {
                    let id = doc.key
                    let data: Dictionary<String, Any> = doc.value
                    let updated_doc = database.document(withID: id)!.toMutable()
                    updated_doc.setData(data)
                    try database.saveDocument(updated_doc)
                }
            }
            
        case "database_updateDocument":
            
            let database: Database = (args.get(name:"database"))!
            let data: Dictionary<String, Any> = args.get(name: "data")!
            let docId: String = args.get(name: "id")!
            let updated_doc = database.document(withID: docId)!.toMutable()
            updated_doc.setData(data)
            try! database.saveDocument(updated_doc)
            
            
        case "database_getDocIds":
            let database: Database = args.get(name:"database")!
            let limit: Int = args.get(name:"limit")!
            let offset: Int = args.get(name:"offset")!
            let query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .limit(Expression.int(limit), offset:Expression.int(offset))

            var result: [String] = []
            do {
                for row in try query.execute() {
                    result.append(row.string(forKey: "id")!)
                }
            }

            return result

        case "database_getDocuments":
            let database: Database = args.get(name:"database")!
            let ids: [String] = args.get(name:"ids")!
            var documents = [String: [String: Any]]()

            for id in ids {
                let document: Document = database.document(withID: id)!
                
                var dict = document.toDictionary()
                for (key, value) in dict {
                    if let list = value as? Dictionary<String, Blob> {
                        var item = Dictionary<String, Any>()
                        for (k, v) in list {
                            item[k] = v.properties
                        }
                        dict[key] = item
                    }
                }
                documents[id] = dict
            }

            return documents
          
        #if COUCHBASE_ENTERPRISE
        case "database_changeEncryptionKey":
            let database: Database = args.get(name:"database")!
            let password: String? = args.get(name:"password")!
            let encryptionKey: EncryptionKey?
            if password == "nil"{
                encryptionKey = nil
            }
            else{
                encryptionKey = EncryptionKey.password(password!)
            }
            do {
                return try database.changeEncryptionKey(encryptionKey)
            } catch {
                print("Got error setting encryption key \(error)")
                return error.localizedDescription
            }
        #endif
        case "database_copy":
            let dbName: String! = args.get(name: "dbName")
            let dbConfig: DatabaseConfiguration? = args.get(name: "dbConfig")
            let dbPath: String! = args.get(name: "dbPath")
            try! Database.copy(fromPath: dbPath, toDatabase: dbName, withConfig: dbConfig)

        case "database_getPreBuiltDb":
            let dbPath: NSString! = args.get(name: "dbPath")
            let path: String! = Bundle(for: type(of:self)).path(forResource: dbPath.deletingPathExtension, ofType: dbPath.pathExtension)
            return path

        case "database_queryAllDocuments":
            let database: Database = args.get(name:"database")!
            let searchQuery = QueryBuilder
                .select(SelectResult.all())
                .from(DataSource.database(database))

            return searchQuery
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return DatabaseRequestHandler.VOID
    }
}

class MyDatabaseChangeListener  {
    var changes: [DatabaseChange] = []
    
    lazy var listener: (DatabaseChange) -> Void = { (change: DatabaseChange) in
        self.changes.append(change)
    }
    
    public func getChanges() -> [DatabaseChange] {
        return changes
    }
}
