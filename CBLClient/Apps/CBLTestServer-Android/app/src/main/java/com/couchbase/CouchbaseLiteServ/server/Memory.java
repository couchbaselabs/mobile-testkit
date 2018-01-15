package com.couchbase.CouchbaseLiteServ.server;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class Memory {
    private Map<String, Object> _memory = new HashMap<>();
    private int _address = 0;

    public <T> T get(String address) {
        return (T)_memory.get(address);
    }

    public String add(Object value) {
        String address = "@" + Integer.toString(++_address);

        _memory.put(address, value);

        return address;
    }

    public void remove(String address) {
        _memory.remove(address);
    }

    public Map<String, Object> get_memory_map(){
        return _memory;
    }

    public void flushMemory(){
        _memory.clear();
        _address = 0;
    }
}