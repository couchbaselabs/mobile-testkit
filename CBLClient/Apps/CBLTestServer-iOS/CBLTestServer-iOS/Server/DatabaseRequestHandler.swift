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
            let name: String? = args.get(name: "name")

            do {
                return try Database(name: name!)
            } catch {
                print("Got error while creating DB \(error)")
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
                print("Got error while deleting DB \(error)")
                return error
            }
        
        case "database_deleteDB":
            let database: Database = args.get(name:"database")!
            
            try database.delete()

        case "database_exists":
            let name: String = args.get(name:"name")!
            let directory: String? = args.get(name:"directory")!
           
            if let directory = directory {
                return Database.exists(withName: name, inDirectory: directory)
            } else {
                return Database.exists(withName: name)
            }

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

            return try? database.saveDocument(document)

        case "database_purge":
            let database: Database = (args.get(name:"database"))!
            let document: Document = args.get(name:"document")!
            
            return try? database.purgeDocument(document)

        case "database_contains":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!

            return database.containsDocument(withID: id)

        case "database_getCount":
            let database: Database = (args.get(name:"database"))!
            return database.count

        case "database_addChangeListener":
            let database: Database = (args.get(name:"database"))!
            let changeListener = MyDatabaseChangeListener()
            database.addChangeListener(changeListener.listener)
            return changeListener

        case "database_removeChangeListener":
            let database: Database = (args.get(name:"database"))!
            let changeListener: ListenerToken = (args.get(name: "changeListener"))!

            database.removeChangeListener(withToken: changeListener)

        case "databaseChangeListener_changesCount":
            let changeListener: MyDatabaseChangeListener = (args.get(name: "changeListener"))!

            return changeListener.getChanges().count

        case "databaseChangeListener_getChange":
            let changeListener: MyDatabaseChangeListener = (args.get(name: "changeListener"))!
            let index: Int = (args.get(name: "index"))!

            return changeListener.getChanges()[index]

        case "databaseChange_getDocumentId":
            let change: DatabaseChange = (args.get(name: "change"))!

            return change.documentIDs

        case "database_saveDocuments":
            let database: Database = args.get(name:"database")!
            let documents: Dictionary<String, Dictionary<String, Any>> = args.get(name: "documents")!

            try database.inBatch {
                for doc in documents {
                    let id = doc.key
                    let data: Dictionary<String, Any> = doc.value
                    let document = MutableDocument(withID: id, data: data)
                    try database.saveDocument(document)
                }
            }

        case "database_getDocIds":
            let database: Database = args.get(name:"database")!
            let query = Query
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))

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
                documents[id] = document.toDictionary()
            }

            return documents

        case "database_queryAllDocuments":
            let database: Database = args.get(name:"database")!
            let searchQuery = Query
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
