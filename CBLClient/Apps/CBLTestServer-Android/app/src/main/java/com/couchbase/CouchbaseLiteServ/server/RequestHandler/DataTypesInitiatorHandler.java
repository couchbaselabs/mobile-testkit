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
/*

    public <T> T[] setArray(Args args){
        T[] arr = args.get("name");
        return arr;
    }

    public HashMap hashMap(Args args){
        return new HashMap();
    }

    public Object get(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");
        return map.get(key);
    }

    public void put(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");
        Object value = args.get("value");
        map.put(key, value);
    }
*/


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
/*
    public Boolean compareHashMap(Args args){
        HashMap first = args.get("first");
        HashMap second = args.get("second");
        Set<String> firstKeys = first.keySet();
        Set<String> secondKeys = second.keySet();
        try{
            for (String key : secondKeys)
            {
                if (!(String.valueOf(first.get(key))).equals(String.valueOf(second.get(key)))){
                    return false;
                }
            }
            for (String key : firstKeys)
            {
                if (!second.containsKey(key)) {
                    return false;
                }
            }
        } catch (NullPointerException np) {
            return false;
        }
        return true;
    }*/
}

