package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Function;

public class FunctionRequestHandler {

    public Expression avg(Args args){
        Object expression = args.get("expression");
        return Function.avg(expression);
    }

    public Expression count(Args args){
        Object expression = args.get("expression");
        return Function.count(expression);
    }

    public Expression min(Args args){
        Object expression = args.get("expression");
        return Function.min(expression);
    }

    public Expression max(Args args){
        Object expression = args.get("expression");
        return Function.max(expression);
    }

    public Expression sum(Args args){
        Object expression = args.get("expression");
        return Function.sum(expression);
    }

//    Not available in DB21
//    public Expression arrayContains(Args args){
//        Object expression = args.get("expression");
//        Object value = args.get("value");
//        return Function.arrayContains(expression, value);
//    }

//    Not available in DB21
//    public Expression arrayLength(Args args){
//        Object expression = args.get("expression");
//        return Function.arrayLength(expression);
//    }

    public Expression abs(Args args){
        Object expression = args.get("expression");
        return Function.abs(expression);
    }

    public Expression acos(Args args){
        Object expression = args.get("expression");
        return Function.acos(expression);
    }

    public Expression asin(Args args){
        Object expression = args.get("expression");
        return Function.asin(expression);
    }

    public Expression atan(Args args){
        Object expression = args.get("expression");
        return Function.atan(expression);
    }

    public Expression atan2(Args args){
        Object x = args.get("x");
        Object y = args.get("y");
        return Function.atan2(x, y);
    }

    public Expression ceil(Args args){
        Object expression = args.get("expression");
        return Function.ceil(expression);
    }

    public Expression cos(Args args){
        Object expression = args.get("expression");
        return Function.cos(expression);
    }

    public Expression degrees(Args args){
        Object expression = args.get("expression");
        return Function.degrees(expression);
    }

    public Expression e(){
        return Function.e();
    }

    public Expression exp(Args args){
        Object expression = args.get("expression");
        return Function.exp(expression);
    }

    public Expression floor(Args args){
        Object expression = args.get("expression");
        return Function.floor(expression);
    }

    public Expression ln(Args args){
        Object expression = args.get("expression");
        return Function.ln(expression);
    }

    public Expression log(Args args){
        Object expression = args.get("expression");
        return Function.log(expression);
    }

    public Expression pi(Args args){
        return Function.pi();
    }

    public Expression power(Args args){
        Object base = args.get("base");
        Object exponent = args.get("exponent");
        return Function.power(base, exponent);
    }

    public Expression radians(Args args){
        Object expression = args.get("expression");
        return Function.radians(expression);
    }

    public Expression round(Args args){
        Object expression = args.get("expression");
        return Function.round(expression);
    }

    public Expression roundDigits(Args args){
        Object expression = args.get("expression");
        int digits = args.get("digits");
        return Function.round(expression, digits);
    }

    public Expression sign(Args args){
        Object expression = args.get("expression");
        return Function.sign(expression);
    }

    public Expression sin(Args args){
        Object expression = args.get("expression");
        return Function.sin(expression);
    }

    public Expression sqrt(Args args){
        Object expression = args.get("expression");
        return Function.sqrt(expression);
    }

    public Expression tan(Args args){
        Object expression = args.get("expression");
        return Function.tan(expression);
    }

    public Expression trunc(Args args){
        Object expression = args.get("expression");
        return Function.trunc(expression);
    }

    public Expression truncDigits(Args args){
        Object expression = args.get("expression");
        int digits = args.get("digits");
        return Function.trunc(expression,digits);
    }

    public Expression contains(Args args){
        Object expression = args.get("expression");
        Object substring = args.get("substring");
        return Function.contains(expression, substring);
    }

    public Expression length(Args args){
        Object expression = args.get("expression");
        return Function.length(expression);
    }

    public Expression lower(Args args){
        Object expression = args.get("expression");
        return Function.lower(expression);
    }

    public Expression ltrim(Args args){
        Object expression = args.get("expression");
        return Function.ltrim(expression);
    }

    public Expression rtrim(Args args){
        Object expression = args.get("expression");
        return Function.rtrim(expression);
    }

    public Expression trim(Args args){
        Object expression = args.get("expression");
        return Function.trim(expression);
    }

    public Expression upper(Args args){
        Object expression = args.get("expression");
        return Function.upper(expression);
    }

    public Expression isArray(Args args){
        Object expression = args.get("expression");
        return Function.isArray(expression);
    }

    public Expression isNumber(Args args){
        Object expression = args.get("expression");
        return Function.isNumber(expression);
    }

    public Expression isDictionary(Args args){
        Object expression = args.get("expression");
        return Function.isDictionary(expression);
    }

//    Not available in DB21
//    public Expression rank(Args args){
//        Expression property = args.get("property");
//        return Function.rank(property);
//    }


}
