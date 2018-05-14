//
//  ExpressionRequestHandler.swift
//  CBLTestServer-iOS
//
//  Created by Raghu Sarangapani on 1/16/18.
//  Copyright © 2018 Raghu Sarangapani. All rights reserved.
//

import Foundation
import CouchbaseLiteSwift


public class ExpressionRequestHandler {
    public static let VOID: String? = nil
    fileprivate var _pushPullReplListener:NSObjectProtocol?
    
    public func handleRequest(method: String, args: Args) throws -> Any? {
        switch method {
        ////////////////
        // Expression //
        ////////////////
        case "expression_property":
            let property: String = args.get(name: "property")!
            return Expression.property(property)

        case "expression_metaId":
            return Meta.id
            
        case "expression_metaSequence":
            return Meta.sequence

        case "expression_parameter":
            let parameter: String = args.get(name: "parameter")!
            return Expression.parameter(parameter)
            
        case "expression_negated":
            let expression: Expression = args.get(name: "expression")!
            return Expression.negated(expression as! ExpressionProtocol)
            
        case "expression_not":
            let expression: Expression = args.get(name: "expression")!
            return Expression.not(expression as! ExpressionProtocol)
        
        case "expression_createEqualTo":
            let expression1: ExpressionProtocol = args.get(name: "expression1")!
            let expression2: ExpressionProtocol = args.get(name: "expression2")!
            return expression1.equalTo(expression2)
            
        case "expression_createAnd":
            let expression1: ExpressionProtocol = args.get(name: "expression1")!
            let expression2: ExpressionProtocol = args.get(name: "expression2")!
            return expression1.and(expression2)
            
        case "expression_createOr":
            let expression1: ExpressionProtocol = args.get(name: "expression1")!
            let expression2: ExpressionProtocol = args.get(name: "expression2")!
            return expression1.or(expression2)
        
        default:
            throw RequestHandlerError.MethodNotFound(method)
        }
    }
}
