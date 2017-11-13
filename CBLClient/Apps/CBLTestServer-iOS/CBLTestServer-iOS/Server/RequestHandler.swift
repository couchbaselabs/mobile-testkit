//
//  RequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 10/31/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum RequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class RequestHandler {
    public static let VOID = NSObject()
    
    public func handleRequest(method: String, args: Args, post_body: Dictionary<String, AnyObject>?) throws -> Any? {
        switch method {
        ///////////
        // Database
        ///////////
        case "database_create":
            let arg: String? = args.get(name: "name")
            guard let name = arg else {
                throw RequestHandlerError.InvalidArgument("name")
            }
            return try Database(name: name)

        case "database_close":
            let database: Database = (args.get(name:"database"))!
            
            try database.close()
            
        case "database_path":
            let database: Database = (args.get(name:"database"))!
            
            return database.path

        case "database_delete":
            //let database: Database = (args.get(name:"database"))!
            let name: String = (args.get(name:"name"))!
            let path: String = (args.get(name:"path"))!

            try Database.delete(name, inDirectory: path)

        case "database_getName":
            let database: Database = args.get(name:"database")!
            
            return database.name
        case "database_getDocument":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!

            return (database.getDocument(id))!
        case "database_save":
            let database: Database = (args.get(name:"database"))!
            let document: Document = args.get(name:"document")!
            
            try! database.save(document)
        case "database_contains":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!
            
            return database.contains(id)
            
        case "database_docCount":
            let database: Database = (args.get(name:"database"))!
            return database.count

        case "database_addDocuments":
            let database: Database = args.get(name:"database")!
            
            try database.inBatch {
                for doc_id in post_body! {
                    let document = Document(doc_id.key, dictionary: (doc_id.value as! Dictionary<String, Any>))
                    try! database.save(document)
                }
            }
            
        case "database_getDocuments":
            let database: Database = args.get(name:"database")!
            let query = Query
                            .select(SelectResult.expression(Expression.meta().id))
                            .from(DataSource.database(database))

            
            do {
                for row in try query.run() {
                    print("Row is \(row)")
                    print("Get docID by property name \(row.string(forKey: "id")))")
                    print("Get docID by column number \(row.string(at: 0)))")
                }
            }

        //////////////
        // Document //
        //////////////
        case "document_create":
            let id: String? = (args.get(name: "id"))
            let dictionary: [String: Any]? = (args.get(name: "dictionary"))
            return Document(id, dictionary: dictionary)

        case "document_delete":
            let database: Database = (args.get(name:"database"))!
            let document: Document = args.get(name:"document")!
            
            try! database.delete(document)
        case "document_getId":
            let document: Document = (args.get(name: "document"))!
            
            return document.id
        case "document_getString":
            let document: Document = (args.get(name: "document"))!
            let property: String = (args.get(name: "property"))!
                
            return document.string(forKey: property)
        case "document_setString":
            let document: Document = (args.get(name: "document"))!
            let property: String = (args.get(name: "property"))!
            let string: String = (args.get(name: "string"))!
            
            document.setString(property, forKey: string)
            
        case "dictionary_create":
            return NSMutableDictionary()
            
        case "dictionary_get":
            let map: [String:Any] = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
                
            return map[key]
            
        case "dictionary_put":
            let map: NSMutableDictionary = args.get(name: "dictionary")!
            let key: String = args.get(name: "key")!
            let string: String = args.get(name: "string")!
            map.setObject(string, forKey: key as NSCopying)

        case "configure_replication":
            let source_db: Database = args.get(name: "source_db")!
            let target_url: String = args.get(name: "target_url")!
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            
            var replicatorType = ReplicatorType.pushAndPull
            if let type = replication_type {
                if type == "push" {
                    replicatorType = .push
                } else if type == "pull" {
                    replicatorType = .pull
                } else {
                    replicatorType = .pushAndPull
                }
            }
            var config = ReplicatorConfiguration(database: source_db, targetURL: URL(string: target_url)!)
            config.replicatorType = replicatorType
            config.continuous = continuous != nil ? continuous! : false
            return Replicator(config: config)

        case "start_replication":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.start()

        case "stop_replication":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.stop()

        case "run_query":
            // Only does select FirstName from test_db where City = "MV"
            let select: String = args.get(name: "select")!
            let frm: Database = args.get(name: "frm")!
            let whr_key: String = args.get(name: "whr_key")!
            let whr_val: String = args.get(name: "whr_val")!

            let query = Query
                .select(SelectResult.expression(Expression.property(select)))
                .from(DataSource.database(frm))
                .where(
                    Expression.property(whr_key).equalTo(whr_val)
                    )

            var response: [String] = []

            do {
                let rows = try query.run()
                for row in rows {
                    response.append(row.string(forKey: select)!)
                }
            } catch let error {
                print(error.localizedDescription)
            }
            return response.flatMap{ String($0) }.map { String($0) }.joined(separator: ",")

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return RequestHandler.VOID;
    }
}
