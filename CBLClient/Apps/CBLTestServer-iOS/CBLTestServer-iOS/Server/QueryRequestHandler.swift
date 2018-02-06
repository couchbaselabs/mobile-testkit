//
//  QueryRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class QueryRequestHandler {
    public static let VOID: String? = nil

    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        /////////////////////
        // ArrayExpression //
        /////////////////////
        case "query_ArrayExpression_variable":
            let name: String = args.get(name: "name")!
            return ArrayExpression.variable(name)

        case "query_ArrayExpression_any":
            let variable: String = args.get(name: "variable")!
            let variableexpression = ArrayExpression.variable(variable)
            return ArrayExpression.any(variableexpression)

        case "query_ArrayExpression_anyAndEvery":
            let variable: String = args.get(name: "variable")!
            let variableexpression = ArrayExpression.variable(variable)
            return ArrayExpression.anyAndEvery(variableexpression)

        case "query_ArrayExpression_every":
            let variable: String = args.get(name: "variable")!
            let variableexpression = ArrayExpression.variable(variable)
            return ArrayExpression.every(variableexpression)

        ///////////////////
        // ArrayFunction //
        ///////////////////
        case "query_ArrayFunction_arrayContains":
            let expression: Expression = args.get(name: "expression")!
            let value: String = args.get(name: "value")!

            return ArrayFunction.contains(expression as! ExpressionProtocol, value: Expression.property(value))

        case "query_ArrayFunction_arrayLength":
            let expression: Expression = args.get(name: "expression")!
            return ArrayFunction.length(expression as! ExpressionProtocol)

        ///////////
        // Joins //
        ///////////
        case "query_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.join(datasource as! DataSourceProtocol)

        case "query_left_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.leftJoin(datasource as! DataSourceProtocol)

        case "query_left_outer_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.leftOuterJoin(datasource as! DataSourceProtocol)

        case "query_inner_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.innerJoin(datasource as! DataSourceProtocol as! DataSourceProtocol)

        case "query_cross_join_datasource":
            let datasource: DataSource = args.get(name: "datasource")!
            return Join.crossJoin(datasource as! DataSourceProtocol)

        ////////////////////////
        // Query SelectResult //
        ////////////////////////
        case "query_select":
            let select_result: SelectResult = args.get(name: "select_result")!

            return QueryBuilder.select(select_result as! SelectResultProtocol)

        case "query_select_distinct":
            let select_result: SelectResult = args.get(name: "select_result")!

            return QueryBuilder.selectDistinct(select_result as! SelectResultProtocol)

        case "query_create":
        // Only does select FirstName from test_db where City = "MV"
            let select_prop: SelectResult = args.get(name: "select_prop")!
            let from_prop: DataSource = args.get(name: "from_prop")!
            let whr_key_prop: Expression = args.get(name: "whr_key_prop")!

            let query = QueryBuilder
                .select(select_prop as! SelectResultProtocol)
                .from(from_prop as! DataSourceProtocol)
                .where(whr_key_prop as! ExpressionProtocol)

            return query

        case "query_run":
            let query: Query = args.get(name: "query")!
            return try query.execute()

        case "query_getDoc":
            let database: Database = args.get(name: "database")!
            let doc_id: String = args.get(name: "doc_id")!

            let searchQuery = QueryBuilder
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .where((Meta.id).equalTo(Expression.string(doc_id)))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_docsLimitOffset":
            let database: Database = args.get(name: "database")!
            let limit: Int = args.get(name: "limit")!
            let offset: Int = args.get(name: "offset")!

            let searchQuery = QueryBuilder
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(Expression.int(limit), offset: Expression.int(offset))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_multipleSelects":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_key: String = args.get(name: "whr_key")!
            let whr_val: String = args.get(name: "whr_val")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where((Expression.property(whr_key)).equalTo(Expression.string(whr_val)))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_whereAndOr":
            let database: Database = args.get(name: "database")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: String = args.get(name: "whr_val2")!
            let whr_key3: String = args.get(name: "whr_key3")!
            let whr_val3: String = args.get(name: "whr_val3")!
            let whr_key4: String = args.get(name: "whr_key4")!
            let whr_val4: Bool = args.get(name: "whr_val4")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(Expression.string(whr_val1))
                    .and(Expression.property(whr_key2).equalTo(Expression.string(whr_val2))
                        .or(Expression.property(whr_key3).equalTo(Expression.string(whr_val3))))
                    .and(Expression.property(whr_key4).equalTo(Expression.boolean(whr_val4))))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_like":
            let database: Database = args.get(name: "database")!
            let whr_key: String = args.get(name: "whr_key")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_val: String = args.get(name: "whr_val")!
            let like_key: String = args.get(name: "like_key")!
            let like_val: String = args.get(name: "like_val")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(Expression.string(whr_val))
                    .and(Expression.property(like_key).like(Expression.string(like_val))))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_regex":
            let database: Database = args.get(name: "database")!
            let whr_key: String = args.get(name: "whr_key")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_val: String = args.get(name: "whr_val")!
            let regex_key: String = args.get(name: "regex_key")!
            let regex_val: String = args.get(name: "regex_val")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(Expression.string(whr_val))
                    .and(Expression.property(regex_key).regex(Expression.string(regex_val))))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_isNullOrMissing":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let limit: Int = args.get(name: "limit")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(select_property1).isNullOrMissing())
                .orderBy(Ordering.expression(Meta.id).ascending())
                .limit(Expression.int(limit))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_ordering":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let whr_key: String = args.get(name: "whr_key")!
            let whr_val: String = args.get(name: "whr_val")!

            let searchQuery = QueryBuilder
                .select(
                    SelectResult.expression(Meta.id),
                    SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(Expression.string(whr_val)))
                .orderBy(Ordering.property(select_property1).ascending())

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_substring":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let substring: String = args.get(name: "substring")!

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Function.upper(Expression.property(select_property2))))
                .from(DataSource.database(database))
                .where(Function.contains(Expression.property(select_property1),                                                                                    substring: Expression.string(substring)))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_collation":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: String = args.get(name: "whr_val2")!
            let equal_to: String = args.get(name: "equal_to")!

            let collator = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true)

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(Expression.string(whr_val1))
                    .and(Expression.property(whr_key2).equalTo(Expression.string(whr_val2)))
                    .and(Expression.property(select_property1).collate(collator).equalTo(Expression.string(equal_to))))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray
               
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
