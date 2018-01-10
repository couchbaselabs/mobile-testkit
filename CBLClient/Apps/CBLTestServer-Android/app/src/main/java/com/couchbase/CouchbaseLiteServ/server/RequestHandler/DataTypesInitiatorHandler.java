package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import java.sql.Blob;
import java.util.HashMap;
import java.util.List;
import java.util.Date;
import java.util.Map;
import java.util.Set;

import com.couchbase.CouchbaseLiteServ.server.Args;

public class DataTypesInitiatorHandler {
    /* ---------------------------------- */
    /* - Initiates Complex Java Objects - */
    /* ---------------------------------- */


    public Date setDate(Args args) {
        return new Date();
    }

    public Double setDouble(Args args){
        Double obj = Double.parseDouble(args.get("value").toString());
        return obj;
    }

    public Float setFloat(Args args){
        Float obj = Float.parseFloat(args.get("value").toString());
        return obj;
    }

    public Long setLong(Args args){
        Long obj = Long.parseLong(args.get("value").toString());
        return obj;
    }

    public Boolean compare(Args args){
        String first = args.get("first").toString();
        String second = args.get("second").toString();
        if (first.equals(second)){
            return true;
        }
        return false;
    }

    public Boolean compareDate(Args args) {
        Date first = args.get("date1");
        Date second = args.get("date2");
        if (first.equals(second)){
            return true;
        }
        return false;
    }

    public Boolean compareDouble(Args args) {
        Double first = args.get("double1");
        Double second = args.get("double2");
        if (first.equals(second)){
            return true;
        }
        return false;
    }

    public Boolean compareLong(Args args) {
        Long first = args.get("long1");
        Long second = args.get("long2");
        if (first.equals(second)){
            return true;
        }
        return false;
    }

}

