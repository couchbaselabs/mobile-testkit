//
//  QueryRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 12/20/17.
//  Copyright © 2017 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

enum QueryRequestHandlerError: Error {
    case MethodNotFound(String)
    case InvalidArgument(String)
}


public class QueryRequestHandler {
    public static let VOID = NSObject()

    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {

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

        ///////////
        // Query //
        ///////////

        case "query_expression_property":
            let property: String = args.get(name: "property")!
            return Expression.property(property)

        case "query_meta_id":
            return Meta.id

        case "query_meta_sequence":
            return Meta.sequence

        case "query_expression_parameter":
            let parameter: String = args.get(name: "parameter")!
            return Expression.parameter(parameter)

        case "query_expression_negated":
            let expression: Any = args.get(name: "expression")!
            return Expression.negated(expression)

        case "query_expression_not":
            let expression: Any = args.get(name: "expression")!
            return Expression.not(expression)

        case "query_ArrayExpression_variable":
            let name: String = args.get(name: "name")!
            return ArrayExpression.variable(name)

        case "query_ArrayExpression_any":
            let variable: String = args.get(name: "variable")!
            return ArrayExpression.any(variable)

        case "query_ArrayExpression_anyAndEvery":
            let variable: String = args.get(name: "variable")!
            return ArrayExpression.anyAndEvery(variable)

        case "query_ArrayExpression_every":
            let variable: String = args.get(name: "variable")!
            return ArrayExpression.every(variable)

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

        case "query_ArrayFunction_arrayContains":
            let expression: Any = args.get(name: "expression")!
            let value: Any = args.get(name: "value")!

            return ArrayFunction.contains(expression, value: value)

        case "query_ArrayFunction_arrayLength":
            let expression: Any = args.get(name: "expression")!
            return ArrayFunction.length(expression)

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
            let indexName: String = args.get(name: "expression")!
            return FullTextFunction.rank(indexName)

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
            return try query.execute()

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
                .where((Meta.id).equalTo(doc_id))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_get_docs_limit_offset":
            let database: Database = args.get(name: "database")!
            let limit: Int = args.get(name: "limit")!
            let offset: Int = args.get(name: "offset")!

            let searchQuery = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(limit,offset: offset)

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
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
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where((Expression.property(whr_key)).equalTo(whr_val))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_where_and_or":
            let database: Database = args.get(name: "database")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: String = args.get(name: "whr_val2")!
            let whr_key3: String = args.get(name: "whr_key3")!
            let whr_val3: String = args.get(name: "whr_val3")!
            let whr_key4: String = args.get(name: "whr_key4")!
            let whr_val4: Bool = args.get(name: "whr_val4")!

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(whr_val1)
                    .and(Expression.property(whr_key2).equalTo(whr_val2)
                        .or(Expression.property(whr_key3).equalTo(whr_val3)))
                    .and(Expression.property(whr_key4).equalTo(whr_val4)))

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

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val)
                    .and(Expression.property(like_key).like(like_val)))

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

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val)
                    .and(Expression.property(regex_key).regex(regex_val)))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray

        case "query_isNullOrMissing":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let limit: Int = args.get(name: "limit")!

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(select_property1).isNullOrMissing())
                .limit(limit)

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

            let searchQuery = Query
                .select(
                    SelectResult.expression(Meta.id),
                    SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val))
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

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Function.upper(Expression.property(select_property2))))
                .from(DataSource.database(database))
                .where(Expression.property(select_property1).and(Function.contains(Expression.property(select_property1),
                                                                                   substring: substring)))

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

            let searchQuery = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(whr_val1)
                    .and(Expression.property(whr_key2).equalTo(whr_val2))
                    .and(Expression.property(select_property1).collate(collator).equalTo(equal_to)))

            var resultArray = [Any]()

            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }

            return resultArray
    
        default:
            throw QueryRequestHandlerError.MethodNotFound(method)
        }
        return QueryRequestHandler.VOID;
    }
}
