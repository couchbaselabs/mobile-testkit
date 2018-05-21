package com.couchbase.CouchbaseLiteServ.server;

import java.util.HashMap;
import java.util.Map;

public class Args {
    private final Map<String, Object> _args = new HashMap<>();

    public void put(String name, Object value) {
        _args.put(name, value);
    }

    public <T> T get(String name) {
        return (T)_args.get(name);
    }

    public boolean contain(String name){
        return _args.containsKey(name);
    }
}