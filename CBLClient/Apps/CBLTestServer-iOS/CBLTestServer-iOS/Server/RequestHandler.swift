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
        //////////////
        // Database //
        //////////////
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
            let document: MutableDocument = args.get(name:"document")!
            
            try! database.save(document)
            
        case "database_contains":
            let database: Database = (args.get(name:"database"))!
            let id: String = (args.get(name: "id"))!
            
            return database.contains(id)
            
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
            let changeListener: DatabaseChange = (args.get(name: "changeListener"))!
            
            database.removeChangeListener(changeListener)

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

        case "database_addDocuments":
            let database: Database = args.get(name:"database")!
            
            try database.inBatch {
                for doc_id in post_body! {
                    let document = MutableDocument(doc_id.key, dictionary: (doc_id.value as! Dictionary<String, Any>))
                    try! database.save(document)
                }
            }
            
        case "database_getDocIds":
            let database: Database = args.get(name:"database")!
            let query = Query
                            .select(SelectResult.expression(Expression.meta().id))
                            .from(DataSource.database(database))

            var result: [String] = []
            do {
                for row in try query.run() {
                    result.append(row.string(forKey: "id")!)
                }
            }

            return String(describing: result)

        case "database_getDocuments":
            let database: Database = args.get(name:"database")!
            let query = Query
                .select(SelectResult.expression(Expression.meta().id))
                .from(DataSource.database(database))
            
            var result: [String: Any] = [:]
            do {
                for row in try query.run() {
                    let id = row.string(forKey: "id")!
                    let doc = database.getDocument(id)?.toDictionary()
                    result[id] = doc
                }
            }
            return try JSONSerialization.data(withJSONObject: result, options: .prettyPrinted)

        //////////////
        // Document //
        //////////////
        case "document_create":
            let id: String? = (args.get(name: "id"))
            let dictionary: [String: Any]? = (args.get(name: "dictionary"))
            return MutableDocument(id, dictionary: dictionary)

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
            let document: MutableDocument = (args.get(name: "document"))!
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

        /////////////////
        // Replication //
        /////////////////

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
        
        /////////////////////
        // Query Collation //
        /////////////////////
            
        case "query_collation_ascii":
            let ignoreCase: Bool = args.get(name: "ignoreCase")!
            
            return Collation.ascii().ignoreCase(ignoreCase)
            
        case "query_collation_unicode":
            return Collation.unicode()
            
        //////////////////////
        // Query DataSource //
        //////////////////////
        case "query_datasource_database":
            let database: Database = args.get(name: "database")!
            return DataSource.database(database)
            
        //////////////////////
        // Query Expression //
        //////////////////////
        case "query_expression_property":
            let property: String = args.get(name: "property")!
            return Expression.property(property)
            
        case "query_expression_meta":
            return Expression.meta()
            
        case "query_expression_parameter":
            let parameter: String = args.get(name: "parameter")!
            return Expression.parameter(parameter)
            
        case "query_expression_negated":
            let expression: Any = args.get(name: "expression")!
            return Expression.negated(expression)
            
        case "query_expression_not":
            let expression: Any = args.get(name: "expression")!
            return Expression.not(expression)
            
        case "query_expression_variable":
            let name: String = args.get(name: "name")!
            return Expression.variable(name)
            
        case "query_expression_any":
            let variable: String = args.get(name: "variable")!
            return Expression.any(variable)
            
        case "query_expression_anyAndEvery":
            let variable: String = args.get(name: "variable")!
            return Expression.anyAndEvery(variable)
            
        case "query_expression_every":
            let variable: String = args.get(name: "variable")!
            return Expression.every(variable)
        
        ////////////////////
        // Query Function //
        ////////////////////
        case "query_function_avg":
            let expression: Any = args.get(name: "expression")!
            return Function.avg(expression)
        
        case "query_function_count":
            let expression: Any = args.get(name: "expression")!
            return Function.count(expression)
            
        case "query_function_min":
            let expression: Any = args.get(name: "expression")!
            return Function.min(expression)
            
        case "query_function_max":
            let expression: Any = args.get(name: "expression")!
            return Function.max(expression)
            
        case "query_function_sum":
            let expression: Any = args.get(name: "expression")!
            return Function.sum(expression)

        ///////////
        // Joins //
        ///////////
        case "query_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.join(datasource)
        
        case "query_left_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.leftJoin(datasource)

        case "query_left_outer_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.leftOuterJoin(datasource)

        case "query_inner_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.innerJoin(datasource)

        case "query_cross_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.crossJoin(datasource)
            
        //////////////////
        // Query Select //
        //////////////////

        case "query_select_result_expression_create":
            let expression: Expression = args.get(name: "expression")!
            
            return SelectResult.expression(expression)

        case "query_select_result_all_create":
            return SelectResult.all()

        case "query_select":
            let select_result: SelectResult = args.get(name: "select_result")!
            
            return Query.select(select_result)

        case "query_select_distinct":
            let select_result: SelectResult = args.get(name: "select_result")!
            
            return Query.selectDistinct(select_result)

        case "query_create":
            // Only does select FirstName from test_db where City = "MV"
            let select_prop: PropertyExpression = args.get(name: "select_prop")!
            let from_prop: DatabaseSource = args.get(name: "from_prop")!
            
            //optional
            let whr_key_prop: PropertyExpression = args.get(name: "whr_key_prop")!
            let whr_val: String = args.get(name: "whr_val")!

            let query = Query
                .select(SelectResult.expression(select_prop))
                .from(from_prop)
                .where(
                    whr_key_prop.equalTo(whr_val)
                    )
            
            return query
            
        case "query_run":
            let query: Query = args.get(name: "query")!
            return try query.run()

        case "query_next_result":
            let query_result_set: ResultSet = args.get(name: "query_result_set")!
            
            return query_result_set.next()

        case "query_result_string":
            let query_result: Result = args.get(name: "query_result")!
            let key: String = args.get(name: "key")!
            
            return query_result.string(forKey: key)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return RequestHandler.VOID;
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

