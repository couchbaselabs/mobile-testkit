package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Function;

public class FunctionRequestHandler {

    public Function avg(Args args){
        Object expression = args.get("expression");
        return Function.avg(expression);
    }

    public Function count(Args args){
        Object expression = args.get("expression");
        return Function.count(expression);
    }

    public Function min(Args args){
        Object expression = args.get("expression");
        return Function.min(expression);
    }

    public Function max(Args args){
        Object expression = args.get("expression");
        return Function.max(expression);
    }

    public Function sum(Args args){
        Object expression = args.get("expression");
        return Function.sum(expression);
    }

    public Function arrayContains(Args args){
        Object expression = args.get("expression");
        Object value = args.get("value");
        return Function.arrayContains(expression, value);
    }

    public Function arrayLength(Args args){
        Object expression = args.get("expression");
        return Function.arrayLength(expression);
    }

    public Function abs(Args args){
        Object expression = args.get("expression");
        return Function.abs(expression);
    }

    public Function acos(Args args){
        Object expression = args.get("expression");
        return Function.acos(expression);
    }

    public Function asin(Args args){
        Object expression = args.get("expression");
        return Function.asin(expression);
    }

    public Function atan(Args args){
        Object expression = args.get("expression");
        return Function.atan(expression);
    }

    public Function atan2(Args args){
        Object x = args.get("x");
        Object y = args.get("y");
        return Function.atan2(x, y);
    }

    public Function ceil(Args args){
        Object expression = args.get("expression");
        return Function.ceil(expression);
    }

    public Function cos(Args args){
        Object expression = args.get("expression");
        return Function.cos(expression);
    }

    public Function degrees(Args args){
        Object expression = args.get("expression");
        return Function.degrees(expression);
    }

    public Function e(){
        return Function.e();
    }

    public Function exp(Args args){
        Object expression = args.get("expression");
        return Function.exp(expression);
    }

    public Function floor(Args args){
        Object expression = args.get("expression");
        return Function.floor(expression);
    }

    public Function ln(Args args){
        Object expression = args.get("expression");
        return Function.ln(expression);
    }

    public Function log(Args args){
        Object expression = args.get("expression");
        return Function.log(expression);
    }

    public Function pi(Args args){
        return Function.pi();
    }

    public Function power(Args args){
        Object base = args.get("base");
        Object exponent = args.get("exponent");
        return Function.power(base, exponent);
    }

    public Function radians(Args args){
        Object expression = args.get("expression");
        return Function.radians(expression);
    }

    public Function round(Args args){
        Object expression = args.get("expression");
        return Function.round(expression);
    }

    public Function roundDigits(Args args){
        Object expression = args.get("expression");
        int digits = args.get("digits");
        return Function.round(expression, digits);
    }

    public Function sign(Args args){
        Object expression = args.get("expression");
        return Function.sign(expression);
    }

    public Function sin(Args args){
        Object expression = args.get("expression");
        return Function.sin(expression);
    }

    public Function sqrt(Args args){
        Object expression = args.get("expression");
        return Function.sqrt(expression);
    }

    public Function tan(Args args){
        Object expression = args.get("expression");
        return Function.tan(expression);
    }

    public Function trunc(Args args){
        Object expression = args.get("expression");
        return Function.trunc(expression);
    }

    public Function truncDigits(Args args){
        Object expression = args.get("expression");
        int digits = args.get("digits");
        return Function.trunc(expression,digits);
    }

    public Function contains(Args args){
        Object expression = args.get("expression");
        Object substring = args.get("substring");
        return Function.contains(expression, substring);
    }

    public Function length(Args args){
        Object expression = args.get("expression");
        return Function.length(expression);
    }

    public Function lower(Args args){
        Object expression = args.get("expression");
        return Function.lower(expression);
    }

    public Function ltrim(Args args){
        Object expression = args.get("expression");
        return Function.ltrim(expression);
    }

    public Function rtrim(Args args){
        Object expression = args.get("expression");
        return Function.rtrim(expression);
    }

    public Function trim(Args args){
        Object expression = args.get("expression");
        return Function.trim(expression);
    }

    public Function upper(Args args){
        Object expression = args.get("expression");
        return Function.upper(expression);
    }

    public Function isArray(Args args){
        Object expression = args.get("expression");
        return Function.isArray(expression);
    }

    public Function isNumber(Args args){
        Object expression = args.get("expression");
        return Function.isNumber(expression);
    }

    public Function isDictionary(Args args){
        Object expression = args.get("expression");
        return Function.isDictionary(expression);
    }

    public Function rank(Args args){
        Expression property = args.get("property");
        return Function.rank(property);
    }


}
