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
            let document: MutableDocument = (args.get(name:"document"))!
            
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

        case "database_saveDocuments":
            let database: Database = args.get(name:"database")!
            let documents: Dictionary<String, Dictionary<String, Any>> = args.get(name: "documents")!
            
            try database.inBatch {
                for doc in documents {
                    let id = doc.key
                    let data: Dictionary<String, Any> = doc.value
                    let document = MutableDocument(id, dictionary: data)
                    try database.save(document)
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

            return result

        case "database_getDocuments":
            let database: Database = args.get(name:"database")!
            let ids: [String] = args.get(name:"ids")!
            var documents = [String: [String: Any]]()

            for id in ids {
                let document: Document = database.getDocument(id)!
                documents[id] = document.toDictionary()
            }
            
            return documents
            
        case "database_queryAllDocuments":
            let database: Database = args.get(name:"database")!
            let searchQuery = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
            
            return searchQuery

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
            
        case "replicator_create_authenticator":
            let authenticatorType: String! = args.get(name: "authentication_type")
            
            if authenticatorType == "session" {
                    let sessionid: String! = args.get(name: "sessionId")
                    let expires: Any? = args.get(name: "expires")
                    let cookiename: String! = args.get(name: "cookieName")
                    return SessionAuthenticator(sessionID: sessionid, expires: expires, cookieName: cookiename)
            }
            else {
                    let username: String! = args.get(name: "username")
                    let password: String! = args.get(name: "password")
                    return BasicAuthenticator(username: username!, password: password!)
            }
            
          
        case "replicator_configureRemoteDbUrl":
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            
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
            let target_converted_url: URL? = URL(string: target_url!)
            if (source_db != nil && target_converted_url != nil) {
                var config = ReplicatorConfiguration(database: source_db!, targetURL: target_converted_url!)
                config.replicatorType = replicatorType
                config.continuous = continuous != nil ? continuous! : false
                config.authenticator = authenticator
                config.conflictResolver = conflictResolver
                config.headers = headers
                
                if channels != nil {
                    config.channels = channels
                }
                if documentIDs != nil {
                    config.documentIDs = documentIDs
                }
                return config
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }
            
        case "replicator_create":
            let config: ReplicatorConfiguration? = args.get(name: "config")
            return Replicator(config: config!)
            
        /*case "configure_replicator_remote_db_url":
            
            let source_db: Database? = args.get(name: "source_db")
            let target_url: String? = args.get(name: "target_url")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let channels: [String]? = args.get(name: "channels")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let authenticator: Authenticator? = args.get(name: "authenticator")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            let headers: Dictionary<String, String>? = args.get(name: "headers")!
            
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
            let target_converted_url: URL? = URL(string: target_url!)
            if (source_db != nil && target_converted_url != nil) {
               var config = ReplicatorConfiguration(database: source_db!, targetURL: target_converted_url!)
               config.replicatorType = replicatorType
               config.continuous = continuous != nil ? continuous! : false
               config.authenticator = authenticator
               config.conflictResolver = conflictResolver
               config.headers = headers
               if channels != nil {
                  config.channels = channels
                }
                if documentIDs != nil {
                    config.documentIDs = documentIDs
                }
                return Replicator(config: config)
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target url provided")
            }
            
        */
        case "configure_replicator_local_db":
            let source_db: Database? = args.get(name: "source_db")
            let targetDatabase: Database? = args.get(name: "targetDatabase")
            let replication_type: String? = args.get(name: "replication_type")!
            let continuous: Bool? = args.get(name: "continuous")
            let documentIDs: [String]? = args.get(name: "documentIDs")
            let conflictResolver: ConflictResolver? = args.get(name: "conflictResolver")
            
            
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
            if (source_db != nil && targetDatabase != nil) {
                var config = ReplicatorConfiguration(database: source_db!, targetDatabase: targetDatabase!)
                config.replicatorType = replicatorType
                config.continuous = continuous != nil ? continuous! : false
                config.conflictResolver = conflictResolver
                if documentIDs != nil {
                    config.documentIDs = documentIDs
                }
                return Replicator(config: config)
            }
            else{
                throw RequestHandlerError.InvalidArgument("No source db provided or target db provided")
            }
            
        case "replicator_start":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.start()

        case "replicator_stop":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            replication_obj.stop()

        case "replicator_status":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let value = replication_obj.status.stringify()
            print("displaying replication status \(value)")
            return value
            
        case "replicator_config":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.config
            
        case "replicator_get_activitylevel":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.activity.hashValue
            
        case "replicator_get_completed":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.completed
            
        case "replicator_get_total":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            return replication_obj.status.progress.total
            
        case "replicator_get_error":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            // if replication_obj.status.error != nil {
                
                return replication_obj.status.error?.localizedDescription
            //}
            // return nil
            
        case "replicator_addChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener = MyReplicationChangeListener()
            let listenerToken = replication_obj.addChangeListener(changeListener.listener)
            changeListener.listenerToken = listenerToken
            return changeListener
            
        case "replicator_removeChangeListener":
            let replication_obj: Replicator = args.get(name: "replication_obj")!
            let changeListener : MyReplicationChangeListener = (args.get(name: "changeListener"))!
            replication_obj.removeChangeListener(changeListener.listenerToken!)
            
        case "replicatorChangeListener_changesCount":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            return changeListener.getChanges().count
            
        case "replicatorChangeListener_getChange":
            let changeListener: MyReplicationChangeListener = (args.get(name: "changeListener"))!
            let index: Int = (args.get(name: "index"))!
            return changeListener.getChanges().description
            
        case "replicator_conflict_resolver":
            let conflict_type: String? = args.get(name: "conflict_type")
            if conflict_type == "mine" {
                return ReplicationMine()
                
            } else if conflict_type == "theirs" {
                return ReplicationTheirs()
            }
            else if conflict_type == "base" {
                return ReplicationBase()
            }
            else {
                func resolve(conflict: Conflict) -> Document? {
                    return nil
                }
            }
            
        
        /////////////////////
        // Query Collation //
        /////////////////////
            
        case "query_collation_ascii":
            let ignoreCase: Bool = args.get(name: "ignoreCase")!
            
            return Collation.ascii().ignoreCase(ignoreCase)
            
        case "query_collation_unicode":
            let ignoreCase: Bool = args.get(name: "ignoreCase")!
            let ignoreAccents: Bool = args.get(name: "ignoreAccents")!
            
            return Collation.unicode().ignoreCase(ignoreCase).ignoreAccents(ignoreAccents)
            
        //////////////////////
        // Query DataSource //
        //////////////////////
        case "query_datasource_database":
            let database: Database = args.get(name: "database")!
            return DataSource.database(database)
            
        //////////////////////
        // Query Expression //
        //////////////////////
            
        
        ///////////
        // Query //
        ///////////

        case "query_expression_property":
            let property: String = args.get(name: "property")!
            return Expression.property(property)
            
        case "query_expression_meta_id":
            return Expression.meta().id
        
        case "query_expression_meta_sequence":
            return Expression.meta().sequence

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
        
        case "create_equalTo_expression":
            let expression1: Expression = args.get(name: "expression1")!
            let expression2: Any = args.get(name: "expression2")!
            return expression1.equalTo(expression2)
            
        case "create_and_expression":
            let expression1: Expression = args.get(name: "expression1")!
            let expression2: Any = args.get(name: "expression2")!
            return expression1.and(expression2)
        
        case "create_or_expression":
            let expression1: Expression = args.get(name: "expression1")!
            let expression2: Any = args.get(name: "expression2")!
            return expression1.or(expression2)

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

        case "query_function_arrayContains":
            let expression: Any = args.get(name: "expression")!
            let value: Any = args.get(name: "value")!

            return Function.arrayContains(expression, value: value)

        case "query_function_arrayLength":
            let expression: Any = args.get(name: "expression")!
            return Function.arrayLength(expression)
            
        case "query_function_abs":
            let expression: Any = args.get(name: "expression")!
            return Function.abs(expression)
            
        case "query_function_acos":
            let expression: Any = args.get(name: "expression")!
            return Function.acos(expression)

        case "query_function_asin":
            let expression: Any = args.get(name: "expression")!
            return Function.asin(expression)
            
        case "query_function_atan":
            let expression: Any = args.get(name: "expression")!
            return Function.atan(expression)

        case "query_function_atan2":
            let x: Any = args.get(name: "x")!
            let y: Any = args.get(name: "y")!

            return Function.atan2(x:x, y:y)

        case "query_function_ceil":
            let expression: Any = args.get(name: "expression")!
            return Function.ceil(expression)
            
        case "query_function_cos":
            let expression: Any = args.get(name: "expression")!
            return Function.cos(expression)
            
        case "query_function_degrees":
            let expression: Any = args.get(name: "expression")!
            return Function.degrees(expression)

        case "query_function_e":
            return Function.e()

        case "query_function_exp":
            let expression: Any = args.get(name: "expression")!
            return Function.exp(expression)
            
        case "query_function_floor":
            let expression: Any = args.get(name: "expression")!
            return Function.floor(expression)
            
        case "query_function_ln":
            let expression: Any = args.get(name: "expression")!
            return Function.ln(expression)
            
        case "query_function_log":
            let expression: Any = args.get(name: "expression")!
            return Function.log(expression)

        case "query_function_pi":
            return Function.pi()
            
        case "query_function_power":
            let base: Any = args.get(name: "base")!
            let exponent: Any = args.get(name: "exponent")!
            
            return Function.power(base:base, exponent:exponent)
            
        case "query_function_radians":
            let expression: Any = args.get(name: "expression")!
            return Function.radians(expression)

        case "query_function_round":
            let expression: Any = args.get(name: "expression")!
            return Function.round(expression)

        case "query_function_round_digits":
            let expression: Any = args.get(name: "expression")!
            let digits: Int = args.get(name: "digits")!

            return Function.round(expression, digits: digits)

        case "query_function_sign":
            let expression: Any = args.get(name: "expression")!
            return Function.sign(expression)

        case "query_function_sin":
            let expression: Any = args.get(name: "expression")!
            return Function.sin(expression)

        case "query_function_sqrt":
            let expression: Any = args.get(name: "expression")!
            return Function.sqrt(expression)

        case "query_function_tan":
            let expression: Any = args.get(name: "expression")!
            return Function.tan(expression)

        case "query_function_trunc":
            let expression: Any = args.get(name: "expression")!
            return Function.trunc(expression)

        case "query_function_trunc_digits":
            let expression: Any = args.get(name: "expression")!
            let digits: Int = args.get(name: "digits")!
            
            return Function.trunc(expression, digits: digits)

        case "query_function_contains":
            let expression: Any = args.get(name: "expression")!
            let substring: Any = args.get(name: "substring")!
            return Function.contains(expression, substring: substring)

        case "query_function_length":
            let expression: Any = args.get(name: "expression")!
            return Function.length(expression)

        case "query_function_lower":
            let expression: Any = args.get(name: "expression")!
            return Function.lower(expression)

        case "query_function_ltrim":
            let expression: Any = args.get(name: "expression")!
            return Function.ltrim(expression)

        case "query_function_rtrim":
            let expression: Any = args.get(name: "expression")!
            return Function.rtrim(expression)

        case "query_function_trim":
            let expression: Any = args.get(name: "expression")!
            return Function.trim(expression)

        case "query_function_upper":
            let expression: Any = args.get(name: "expression")!
            return Function.upper(expression)

        case "query_function_isArray":
            let expression: Any = args.get(name: "expression")!
            return Function.isArray(expression)

        case "query_function_isNumber":
            let expression: Any = args.get(name: "expression")!
            return Function.isNumber(expression)

        case "query_function_isDictionary":
            let expression: Any = args.get(name: "expression")!
            return Function.isDictionary(expression)

        case "query_function_isString":
            let expression: Any = args.get(name: "expression")!
            return Function.isString(expression)

        case "query_function_rank":
            let property: Expression = args.get(name: "expression")!
            return Function.rank(property)
            
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
            
        ////////////////////////
        // Query SelectResult //
        ////////////////////////

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
            let select_prop: SelectResult = args.get(name: "select_prop")!
            let from_prop: DatabaseSource = args.get(name: "from_prop")!
            let whr_key_prop: Expression = args.get(name: "whr_key_prop")!

            let query = Query
                .select(select_prop)
                .from(from_prop)
                .where(whr_key_prop)
            
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
            
        case "query_get_doc":
            let database: Database = args.get(name: "database")!
            let doc_id: String = args.get(name: "doc_id")!

            let searchQuery = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .where((Expression.meta().id).equalTo(doc_id))

            for row in try searchQuery.run() {
                return row.toDictionary()
            }
            
        case "query_get_docs_limit_offset":
            let database: Database = args.get(name: "database")!
            let limit: Int = args.get(name: "limit")!
            let offset: Int = args.get(name: "offset")!
            
            let searchQuery = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(limit,offset: offset)
            
            var resultArray = [Any]()

            for row in try searchQuery.run() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_multiple_selects":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_key: String = args.get(name: "whr_key")!
            let whr_val: String = args.get(name: "whr_val")!

            let searchQuery = Query
                .select(SelectResult.expression(Expression.meta().id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where((Expression.property(whr_key)).equalTo(whr_val))
            
            var resultArray = [Any]()
            
            for row in try searchQuery.run() {
                resultArray.append(row.toDictionary())
            }
            
            print ("resultArray is \(resultArray)")
            return resultArray
           
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

class MyReplicationChangeListener : NSObject  {
    var repl_changes: [ReplicatorChange] = []
    
    var listenerToken: NSObjectProtocol?
    
    lazy var listener: (ReplicatorChange) -> Void = { (change: ReplicatorChange) in
        self.repl_changes.append(change)
    }
    
    public func getChanges() -> [ReplicatorChange] {
        NSLog("GOT repl CHANGES .......\(repl_changes)")
        return repl_changes
    }
}

class ReplicationMine: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.mine
    }
}

class ReplicationTheirs: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.theirs
    }
}

class ReplicationBase: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return conflict.base
    }
}

class GiveUp: ConflictResolver {
    func resolve(conflict: Conflict) -> Document? {
        return nil
    }
}

