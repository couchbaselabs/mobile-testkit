//
//  DatabaseRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum DatabaseRequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class DatabaseRequestHandler {
    public static let VOID = NSObject()
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {

        //////////////
        // Database //
        //////////////
        case "database_create":
            let arg: String? = args.get(name: "name")
            print("args of database_create \(arg!)")
            guard let name = arg else {
                throw DatabaseRequestHandlerError.InvalidArgument("name")
            }
            return try Database(name: name)

        case "database_close":
            let database: Database = (args.get(name:"database"))!

            try database.close()

        case "database_path":
            let database: Database = (args.get(name:"database"))!

            return database.path

        case "database_delete":
            let name: String = (args.get(name:"name"))!
            let path: String = (args.get(name:"path"))!

            try Database.delete(withName: name, inDirectory: path)

        case "database_getName":
            let database: Database = args.get(name:"database")!

            return database.name

        case "database_document":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!

            return (database.document(withID: id))!

        case "database_save":
            let database: Database = (args.get(name:"database"))!
            let document: MutableDocument = args.get(name:"document")!

            try! database.saveDocument(document)

        case "database_contains":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!

            return database.containsDocument(withID: id)

        case "database_docCount":
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
            throw DatabaseRequestHandlerError.MethodNotFound(method)
        }
        return DatabaseRequestHandler.VOID;
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
