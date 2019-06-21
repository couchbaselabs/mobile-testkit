package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.ArrayExpression;
import com.couchbase.lite.ArrayExpressionIn;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Meta;
import com.couchbase.lite.MetaExpression;
import com.couchbase.lite.PropertyExpression;
import com.couchbase.lite.VariableExpression;


public class ExpressionRequestHandler {

    public PropertyExpression property(Args args) {
        String property = args.get("property");
        return Expression.property(property);
    }

    public MetaExpression metaId() {
        return Meta.id;
    }

    public MetaExpression metaSequence() {
        return Meta.sequence;
    }

    public Expression parameter(Args args) {
        String parameter = args.get("parameter");
        return Expression.parameter(parameter);
    }

    public Expression negated(Args args) {
        Expression expression = args.get("expression");
        return Expression.negated(expression);
    }


    public Expression not(Args args) {
        Expression expression = args.get("expression");
        return Expression.not(expression);
    }

    public VariableExpression variable(Args args) {
        String name = args.get("name");
        return ArrayExpression.variable(name);
    }


    public ArrayExpressionIn any(Args args) {
        VariableExpression variable = args.get("variable");
        return ArrayExpression.any(variable);
    }


    public ArrayExpressionIn anyAndEvery(Args args) {
        VariableExpression variable = args.get("variable");
        return ArrayExpression.anyAndEvery(variable);
    }


    public ArrayExpressionIn every(Args args) {
        VariableExpression variable = args.get("variable");
        return ArrayExpression.every(variable);
    }


    public Expression createEqualTo(Args args) {
        Expression expression1 = args.get("expression1");
        Expression expression2 = args.get("expression2");
        return expression1.equalTo(expression2);
    }


    public Expression createAnd(Args args) {
        Expression expression1 = args.get("expression1");
        Expression expression2 = args.get("expression2");
        return expression1.and(expression2);
    }

    public Expression createOr(Args args) {
        Expression expression1 = args.get("expression1");
        Expression expression2 = args.get("expression2");
        return expression1.or(expression2);
    }

}
