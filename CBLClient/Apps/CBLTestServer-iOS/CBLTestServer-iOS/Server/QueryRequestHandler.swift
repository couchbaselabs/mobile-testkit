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
            return Join.innerJoin(datasource as! DataSourceProtocol)

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

        case "query_multipleSelectsDoubleValue":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_key: String = args.get(name: "whr_key")!
            let whr_val: Float = args.get(name: "whr_val")!
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where((Expression.property(whr_key)).equalTo(Expression.float(whr_val)))
            
            var resultArray = [Any]()
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_multipleSelectsOrderByLocaleValue":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_key: String = args.get(name: "whr_key")!
            let locale: String = args.get(name: "locale")!
            let with_locale = Collation.unicode().locale(locale)
            let key = Expression.property(whr_key)
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .orderBy(Ordering.expression(key.collate(with_locale)))
            
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

        case "query_arthimetic":
            let database: Database = args.get(name: "database")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property("number1").modulo(Expression.int(2)).equalTo(Expression.int(0)))
            
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
            
        case "query_join":
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let select_property3: String = args.get(name: "select_property3")!
            let select_property4: String = args.get(name: "select_property4")!
            let select_property5: String = args.get(name: "select_property5")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: String = args.get(name: "whr_val2")!
            let whr_key3: String = args.get(name: "whr_key3")!
            let whr_val3: String = args.get(name: "whr_val3")!
            let join_key: String = args.get(name: "join_key")!
            let main: String = "route"
            let secondary: String = "airline"
            
            let searchQuery = QueryBuilder
                .selectDistinct(SelectResult.expression(Expression.property(select_property1).from(secondary)),
                                SelectResult.expression(Expression.property(select_property2).from(secondary)),
                                SelectResult.expression(Expression.property(select_property3).from(main)),
                                SelectResult.expression(Expression.property(select_property4).from(main)),
                                SelectResult.expression(Expression.property(select_property5).from(main)))
                .from(DataSource.database(database).as(main))
                .join(Join.join(DataSource.database(database).as(secondary))
                    .on(Meta.id.from(secondary).equalTo(Expression.property(join_key).from(main))))
                .where(Expression.property(whr_key1).from(main).equalTo(Expression.string(whr_val1))
                    .and(Expression.property(whr_key2).from(secondary).equalTo(Expression.string(whr_val2)))
                    .and(Expression.property(whr_key3).from(main).equalTo(Expression.string(whr_val3))))
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_leftJoin":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "select_property")!
            let limit: Int = args.get(name: "limit")!
            let main: String = "airline"
            let secondary: String = "route"
            
            let searchQuery = QueryBuilder
                .select(SelectResult.all().from(main),
                        SelectResult.all().from((secondary)))
                .from(DataSource.database(database).as(main))
                .join(Join.leftJoin(DataSource.database(database).as(secondary))
                    .on(Meta.id.from(main).equalTo(Expression.property(prop).from(secondary))))
                //.orderBy(Ordering.expression(Expression.property(prop).from(secondary)).ascending())
                .limit(Expression.int(limit))

            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_leftOuterJoin":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "select_property")!
            let limit: Int = args.get(name: "limit")!
            let main: String = "airline"
            let secondary: String = "route"
            
            let searchQuery = QueryBuilder
                .select(SelectResult.all().from(main),
                        SelectResult.all().from((secondary)))
                .from(DataSource.database(database).as(main))
                .join(Join.leftOuterJoin(DataSource.database(database).as(secondary))
                    .on(Meta.id.from(main).equalTo(Expression.property(prop).from(secondary))))
                //.orderBy(Ordering.expression(Expression.property(prop).from(secondary)).ascending())
                .limit(Expression.int(limit))
            
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            return resultArray

        case "query_innerJoin":
            /*
             SELECT
             employeeDS.firstname,
             employeeDS.lastname,
             departmentDS.name
             FROM
             `travel-sample` employeeDS
             INNER JOIN `travel-sample` departmentDS ON employeeDS.department = departmentDS.code
             WHERE
             employeeDS.type = "employee"
             AND departmentDS.type = "department"
             */
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let select_property3: String = args.get(name: "select_property3")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: Int = args.get(name: "whr_val2")!
            let limit: Int = args.get(name: "limit")!
            let join_key1: String = args.get(name: "join_key1")!
            let join_key2: String = args.get(name: "join_key2")!
            let main: String = "route"
            let secondary: String = "airline"
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Expression.property(select_property1).from(main)),
                        SelectResult.expression(Expression.property(select_property2).from(main)),
                        SelectResult.expression(Expression.property(select_property3).from(secondary)))
                .from(DataSource.database(database).as(main))
                .join(Join.innerJoin(DataSource.database(database).as(secondary))
                    .on(Expression.property(join_key1).from(secondary).equalTo(Expression.property(join_key2).from(main))
                        .and(Expression.property(whr_key1).from(secondary).equalTo(Expression.string(whr_val1)))
                        .and(Expression.property(whr_key2).from(main).equalTo(Expression.int(whr_val2)))))
                .limit(Expression.int(limit))
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_crossJoin":
            /*
             SELECT
             departmentDS.name AS DeptName,
             locationDS.name AS LocationName,
             locationDS.address
             FROM
             `travel-sample` departmentDS
             CROSS JOIN `travel-sample` locationDS
             WHERE
             departmentDS.type = "department"
             */
            let database: Database = args.get(name: "database")!
            let select_property1: String = args.get(name: "select_property1")!
            let select_property2: String = args.get(name: "select_property2")!
            let whr_key1: String = args.get(name: "whr_key1")!
            let whr_val1: String = args.get(name: "whr_val1")!
            let whr_key2: String = args.get(name: "whr_key2")!
            let whr_val2: String = args.get(name: "whr_val2")!
            let limit: Int = args.get(name: "limit")!
            let main: String = "airport"
            let secondary: String = "airline"
            let first_name: String = "firstName"
            let second_name: String = "secondName"
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Expression.property(select_property1).from(main)).as(first_name),
                        SelectResult.expression(Expression.property(select_property1).from(secondary)).as(second_name),
                        SelectResult.expression(Expression.property(select_property2).from(secondary)))
                .from(DataSource.database(database).as(main))
                .join(Join.crossJoin(DataSource.database(database).as(secondary)))
                .where(Expression.property(whr_key1).from(main).equalTo(Expression.string(whr_val1))
                    .and(Expression.property(whr_key2).from(secondary).equalTo(Expression.string(whr_val2))))
                .limit(Expression.int(limit))
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_equalTo":
            let database: Database = args.get(name: "database")!
            let val: String = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).equalTo(Expression.string(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_notEqualTo":
            let database: Database = args.get(name: "database")!
            let val: String = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).notEqualTo(Expression.string(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_greaterThan":
            let database: Database = args.get(name: "database")!
            let val: Int = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).greaterThan(Expression.int(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_greaterThanOrEqualTo":
            let database: Database = args.get(name: "database")!
            let val: Int = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).greaterThanOrEqualTo(Expression.int(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_lessThan":
            let database: Database = args.get(name: "database")!
            let val: Int = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).lessThan(Expression.int(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_lessThanOrEqualTo":
            let database: Database = args.get(name: "database")!
            let val: Int = args.get(name: "val")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).lessThanOrEqualTo(Expression.int(val)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_between":
            let database: Database = args.get(name: "database")!
            let val1: Int = args.get(name: "val1")!
            let val2: Int = args.get(name: "val2")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).between(Expression.int(val1), and: Expression.int(val2)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_in":
            let database: Database = args.get(name: "database")!
            let val1: String = args.get(name: "val1")!
            let val2: String = args.get(name: "val2")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).in([Expression.string(val1), Expression.string(val2)]))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_is":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(prop).is(Expression.string(nil)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_anyOperator":
            let database: Database = args.get(name: "database")!
            let collection: String = args.get(name: "collection")!
            let collection_prop: String = args.get(name: "collection_prop")!
            let collection_val: String = args.get(name: "collection_val")!
            let whr_prop: String = args.get(name: "whr_prop")!
            let whr_val: String = args.get(name: "whr_val")!
            let departure = ArrayExpression.variable(collection)
            let departure_utc = ArrayExpression.variable(collection_prop)
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(whr_prop).equalTo(Expression.value(whr_val)
                    .and(ArrayExpression.any(departure).in(Expression.property(collection))
                        .satisfies(departure_utc.greaterThan(Expression.value(collection_val))))))
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray

        case "query_not":
            let database: Database = args.get(name: "database")!
            let val1: Int = args.get(name: "val1")!
            let val2: Int = args.get(name: "val2")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.not(Expression.property(prop).between(Expression.int(val1), and: Expression.int(val2))))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_isNot":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "prop")!
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(database))
                .where(Expression.property(prop).isNot(Expression.string(nil)))
                .orderBy(Ordering.expression(Meta.id).ascending())
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
        
        case "query_singlePropertyFTS":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "prop")!
            let val: String = args.get(name: "val")!
            let doc_type: String = args.get(name: "doc_type")!
            let limit: Int = args.get(name: "limit")!
            let stemming: Bool = args.get(name: "stemming")!
            let index: String = "singlePropertyIndex"
            let ftsIndex:FullTextIndex

            if stemming{
                ftsIndex = IndexBuilder.fullTextIndex(items: FullTextIndexItem.property(prop))
            } else {
                ftsIndex = IndexBuilder.fullTextIndex(items: FullTextIndexItem.property(prop)).language(nil)
            }
            try database.createIndex(ftsIndex, withName: index)
            let ftsExpression = FullTextExpression.index(index)

            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(database))
                .where(Expression.property("type").equalTo(Expression.string(doc_type)).and(ftsExpression.match(val)))
                .limit(Expression.int(limit))
            
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
            
        case "query_multiplePropertyFTS":
            let database: Database = args.get(name: "database")!
            let prop1: String = args.get(name: "prop1")!
            let prop2: String = args.get(name: "prop2")!
            let val: String = args.get(name: "val")!
            let doc_type: String = args.get(name: "doc_type")!
            let stemming: Bool = args.get(name: "stemming")!
            let limit: Int = args.get(name: "limit")!
            let index: String = "multiplePropertyIndex"

            let ftsIndex:FullTextIndex
            if stemming{
                ftsIndex = IndexBuilder.fullTextIndex(items: FullTextIndexItem.property(prop1), FullTextIndexItem.property(prop2))
            } else {
                ftsIndex = IndexBuilder.fullTextIndex(items: FullTextIndexItem.property(prop1), FullTextIndexItem.property(prop2)).language(nil)
            }
            try database.createIndex(ftsIndex, withName: index)
            let ftsExpression = FullTextExpression.index(index)
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop1)),
                        SelectResult.expression(Expression.property(prop2)))
                .from(DataSource.database(database))
                .where(Expression.property("type").equalTo(Expression.string(doc_type)).and(ftsExpression.match(val)))
                .limit(Expression.int(limit))
            
            var resultArray = [Any]()
            
            for row in try searchQuery.execute() {
                resultArray.append(row.toDictionary())
            }
            
            return resultArray
        
        case "query_ftsWithRanking":
            let database: Database = args.get(name: "database")!
            let prop: String = args.get(name: "prop")!
            let val: String = args.get(name: "val")!
            let doc_type: String = args.get(name: "doc_type")!
            let limit: Int = args.get(name: "limit")!
            let index: String = "singlePropertyIndex"
            
            let ftsIndex = IndexBuilder.fullTextIndex(items: FullTextIndexItem.property(prop)).language(nil)
            try database.createIndex(ftsIndex, withName: index)
            let ftsExpression = FullTextExpression.index(index)
            
            let searchQuery = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(database))
                .where(Expression.property("type").equalTo(Expression.string(doc_type)).and(ftsExpression.match(val)))
                .orderBy(Ordering.expression(FullTextFunction.rank(index)).descending())
                .limit(Expression.int(limit))
            
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
