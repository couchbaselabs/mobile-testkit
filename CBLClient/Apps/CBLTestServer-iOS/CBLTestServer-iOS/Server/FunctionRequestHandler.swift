//
//  FunctionRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift

public class FunctionRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        //////////////
        // Function //
        //////////////
        case "function_avg":
            let expression: Expression = args.get(name: "expression")!
            return Function.avg(expression)
            
        case "function_count":
            let expression: Expression = args.get(name: "expression")!
            return Function.count(expression)
            
        case "function_min":
            let expression: Expression = args.get(name: "expression")!
            return Function.min(expression)
            
        case "function_max":
            let expression: Expression = args.get(name: "expression")!
            return Function.max(expression)
            
        case "function_sum":
            let expression: Expression = args.get(name: "expression")!
            return Function.sum(expression)
            
        case "function_abs":
            let expression: Expression = args.get(name: "expression")!
            return Function.abs(expression)
            
        case "function_acos":
            let expression: Expression = args.get(name: "expression")!
            return Function.acos(expression)
            
        case "function_asin":
            let expression: Expression = args.get(name: "expression")!
            return Function.asin(expression)
            
        case "function_atan":
            let expression: Expression = args.get(name: "expression")!
            return Function.atan(expression)
            
        case "function_atan2":
            let x: Float = args.get(name: "x")!
            let y: Float = args.get(name: "y")!
            
            return Function.atan2(x:Expression.float(x), y:Expression.float(y))
            
        case "function_ceil":
            let expression: Expression = args.get(name: "expression")!
            return Function.ceil(expression)
            
        case "function_cos":
            let expression: Expression = args.get(name: "expression")!
            return Function.cos(expression)
            
        case "function_degrees":
            let expression: Expression = args.get(name: "expression")!
            return Function.degrees(expression)
            
        case "function_e":
            return Function.e()
            
        case "function_exp":
            let expression: Expression = args.get(name: "expression")!
            return Function.exp(expression)
            
        case "function_floor":
            let expression: Expression = args.get(name: "expression")!
            return Function.floor(expression)
            
        case "function_ln":
            let expression: Expression = args.get(name: "expression")!
            return Function.ln(expression)
            
        case "function_log":
            let expression: Expression = args.get(name: "expression")!
            return Function.log(expression)
            
        case "function_pi":
            return Function.pi()
            
        case "function_power":
            let base: Int = args.get(name: "base")!
            let exponent: Int = args.get(name: "exponent")!
            
            return Function.power(base: Expression.int(base), exponent:Expression.int(exponent))
            
        case "function_radians":
            let expression: Expression = args.get(name: "expression")!
            return Function.radians(expression)
            
        case "function_round":
            let expression: Expression = args.get(name: "expression")!
            return Function.round(expression)
            
        case "function_roundDigits":
            let expression: Expression = args.get(name: "expression")!
            let digits: Int = args.get(name: "digits")!
            
            return Function.round(expression, digits: Expression.int(digits))
            
        case "function_sign":
            let expression: Expression = args.get(name: "expression")!
            return Function.sign(expression)
            
        case "function_sin":
            let expression: Expression = args.get(name: "expression")!
            return Function.sin(expression)
            
        case "function_sqrt":
            let expression: Expression = args.get(name: "expression")!
            return Function.sqrt(expression)
            
        case "function_tan":
            let expression: Expression = args.get(name: "expression")!
            return Function.tan(expression)
            
        case "function_trunc":
            let expression: Expression = args.get(name: "expression")!
            return Function.trunc(expression)
            
        case "function_truncDigits":
            let expression: Expression = args.get(name: "expression")!
            let digits: Int = args.get(name: "digits")!
            
            return Function.trunc(expression, digits: Expression.int(digits))
            
        case "function_contains":
            let expression: Expression = args.get(name: "expression")!
            let substring: Expression = args.get(name: "substring")!
            return Function.contains(expression, substring: substring)
            
        case "function_length":
            let expression: Expression = args.get(name: "expression")!
            return Function.length(expression)
            
        case "function_lower":
            let expression: Expression = args.get(name: "expression")!
            return Function.lower(expression)
            
        case "function_ltrim":
            let expression: Expression = args.get(name: "expression")!
            return Function.ltrim(expression)
            
        case "function_rtrim":
            let expression: Expression = args.get(name: "expression")!
            return Function.rtrim(expression)
            
        case "function_trim":
            let expression: Expression = args.get(name: "expression")!
            return Function.trim(expression)
            
        case "function_upper":
            let expression: Expression = args.get(name: "expression")!
            return Function.upper(expression)
            
        case "function_isArray":
            let expression: Expression = args.get(name: "expression")!
            //return Function.isArray(expression)
            
        case "function_isNumber":
            let expression: Expression = args.get(name: "expression")!
            //return Function.isNumber(expression)
            
        case "function_isDictionary":
            let expression: Expression = args.get(name: "expression")!
            //return Function.isDictionary(expression)
            
        case "function_isString":
            let expression: Expression = args.get(name: "expression")!
            //return Function.isString(expression)
            
        case "function_rank":
            let indexName: String = args.get(name: "expression")!
            return FullTextFunction.rank(indexName)

        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
        return FunctionRequestHandler.VOID
    }
}
