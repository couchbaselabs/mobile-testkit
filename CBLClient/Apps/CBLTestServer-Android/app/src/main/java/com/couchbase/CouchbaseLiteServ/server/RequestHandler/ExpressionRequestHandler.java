package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Meta;

public class ExpressionRequestHandler {

    public Expression.PropertyExpression property(Args args) {
        String property = args.get("property");
        return Expression.property(property);
    }

    //Need to check the signature of this method
    public Meta.MetaExpression metaId() {
        return Expression.meta().getId();
    }

    //Need to check the signature of this method
    public Meta.MetaExpression metaSequence() {
        return Expression.meta().getSequence();
    }

    public Expression parameter(Args args) {
        String parameter = args.get("parameter");
        return Expression.parameter(parameter);
    }

    public Expression negated(Args args) {
        Object expression = args.get("expression");
        return Expression.negated(expression);
    }


    public Expression not(Args args) {
        Object expression = args.get("expression");
        return Expression.not(expression);
    }


    public Expression variable(Args args) {
        String name = args.get("name");
        return Expression.variable(name);
    }


    public Expression.In any(Args args) {
        String variable = args.get("variable");
        return Expression.any(variable);
    }


    public Expression.In anyAndEvery(Args args) {
        String variable = args.get("variable");
        return Expression.anyAndEvery(variable);
    }


    public Expression.In every(Args args) {
        String variable = args.get("variable");
        return Expression.every(variable);
    }


    public Expression createEqualTo(Args args) {
        Expression expression1 = args.get("expression1");
        Object expression2 = args.get("expression2");
        return expression1.equalTo(expression2);
    }


    public Expression createAnd(Args args) {
        Expression expression1 = args.get("expression1");
        Object expression2 = args.get("expression2");
        return expression1.and(expression2);
    }

    public Expression or(Args args) {
        Expression expression1 = args.get("expression1");
        Object expression2 = args.get("expression2");
        return expression1.or(expression2);
    }

}
