package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import java.util.Date;

import com.couchbase.CouchbaseLiteServ.server.Args;


public class DataTypesInitiatorHandler {
    /* ---------------------------------- */
    /* - Initiates Complex Java Objects - */
    /* ---------------------------------- */


    public Date setDate(Args args) {
        return new Date();
    }

    public Double setDouble(Args args) {
        return Double.parseDouble(args.get("value").toString());
    }

    public Float setFloat(Args args) {
        return Float.parseFloat(args.get("value").toString());
    }

    public Long setLong(Args args) {
        return Long.parseLong(args.get("value").toString());
    }

    public Boolean compare(Args args) {
        String first = args.get("first").toString();
        String second = args.get("second").toString();
        return first.equals(second);
    }

    public Boolean compareDate(Args args) {
        Date first = args.get("date1");
        Date second = args.get("date2");
        return first.equals(second);
    }

    public Boolean compareDouble(Args args) {
        Double first = Double.valueOf(args.get("double1").toString());
        Double second = Double.valueOf(args.get("double2").toString());
        return first.equals(second);
    }

    public Boolean compareLong(Args args) {
        Long first = args.get("long1");
        Long second = args.get("long2");
        return first.equals(second);
    }

}

