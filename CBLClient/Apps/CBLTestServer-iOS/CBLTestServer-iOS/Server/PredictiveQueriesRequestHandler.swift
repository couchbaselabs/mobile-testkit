//
//  PredictiveQueriesRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Sridevi Saragadam on 2/20/19.
//  Copyright © 2017 Sridevi Saragadam. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class PredictiveQueriesRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
            
        case "predictiveQuery_registerModel":
            let modelName: String = args.get(name: "model_name")!
            let echoModel = EchoModel(name: modelName)
            Database.prediction.registerModel(echoModel, withName: modelName)
            return echoModel
        
        case "predictiveQuery_unRegisterModel":
            let modelName: String = args.get(name: "model_name")!
            Database.prediction.unregisterModel(withName: modelName)
        
        case "predictiveQuery_getPredictionQueryResult":
            let model: EchoModel = args.get(name: "model")!
            
            //let dict: [String: Any] = ["friend_one": Expression.property("friend_one")]
            
            let dict: [String: Any] = args.get(name: "dictionary")!
            let database: Database = args.get(name: "database")!
            let input = Expression.value(dict)
            let prediction = Function.prediction(model: model.name, input: input)
            let queryResult = QueryBuilder
                .select(SelectResult.expression(prediction))
                 .from(DataSource.database(database))
            
            var resultArray = [Any]()
            
            for row in try queryResult.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "predictiveQuery_nonDictionary":
            let model: EchoModel = args.get(name: "model")!
            
            //let dict: [String: Any] = ["friend_one": Expression.property("friend_one")]
            
            let text: String = args.get(name: "dictionary")!
            let database: Database = args.get(name: "database")!
            let input = Expression.value(text)
            let prediction = Function.prediction(model: model.name, input: input)
            let queryResult = QueryBuilder
                .select(SelectResult.expression(prediction))
                .from(DataSource.database(database))
            // return try queryResult.execute()
            do{
                try queryResult.execute();
            }
            catch {
              return error.localizedDescription
            }
            
        case "predictiveQuery_getNumberOfCalls":
            let model: EchoModel = args.get(name: "model")!
            return model.numberOfCalls
            
        case "predictiveQuery_euclideanDistance":
            let database: Database = args.get(name: "database")!
            let key1: String = args.get(name: "key1")!
            let key2: String = args.get(name: "key2")!
            let key3_distance = Function.euclideanDistance(between: Expression.property(key1),
                                                      and: Expression.property(key2))
            let queryResult = QueryBuilder
                .select(SelectResult.expression(key3_distance))
                .from(DataSource.database(database))
            var resultArray = [Any]()
            
            for row in try queryResult.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "predictiveQuery_squaredEuclideanDistance":
            let database: Database = args.get(name: "database")!
            let key1: String = args.get(name: "key1")!
            let key2: String = args.get(name: "key2")!
            let distance = Function.squaredEuclideanDistance(between: Expression.property(key1),
                                                           and: Expression.property(key2))
            let queryResult = QueryBuilder
                .select(SelectResult.expression(distance))
                .from(DataSource.database(database))
            var resultArray = [Any]()
            
            for row in try queryResult.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "predictiveQuery_cosineDistance":
            let database: Database = args.get(name: "database")!
            let key1: String = args.get(name: "key1")!
            let key2: String = args.get(name: "key2")!
            let distance = Function.cosineDistance(between: Expression.property(key1),
                                                             and: Expression.property(key2))
            let queryResult = QueryBuilder
                .select(SelectResult.expression(distance))
                .from(DataSource.database(database))
            var resultArray = [Any]()
            
            for row in try queryResult.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
        
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return PredictiveQueriesRequestHandler.VOID
    }
}

class EchoModel: PredictiveModel {
    
    let name: String
    var numberOfCalls = 0
    
    init(name: String) {
        self.name = name
    }
    
    func predict(input: DictionaryObject) -> DictionaryObject? {
        numberOfCalls = numberOfCalls + 1
        return input;
    }
    
}
