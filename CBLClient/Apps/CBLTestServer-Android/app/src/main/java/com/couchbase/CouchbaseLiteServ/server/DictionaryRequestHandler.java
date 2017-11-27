package com.couchbase.CouchbaseLiteServ.server;


import com.couchbase.lite.Array;
import com.couchbase.lite.Blob;
import com.couchbase.lite.Database;
import com.couchbase.lite.Dictionary;
import com.couchbase.lite.Document;
import com.couchbase.litecore.fleece.FLEncoder;

import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

public class DictionaryRequestHandler{
    /* -------------- */
    /* - Dictionary - */
    /* -------------- */

    public Map create(Args args) {
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
        String string = args.get("string");

        map.put(key, string);
    }

    public int count(Args args){
        Document dictionary = args.get("dictionary");
        return dictionary.count();
    }

    public void fleeceEncode(Args args){
        Document dictionary = args.get("dictionary");
        FLEncoder encoder = args.get("encoder");
        Database database = args.get("database");
        dictionary.fleeceEncode(encoder, database);
    }

    public Dictionary set(Args args){
        Dictionary dictionary = args.get("dictionary");
        Map<String, Object> content_dict  = args.get("content_dict");
        return dictionary.set(content_dict);
    }


    public String getString(Args args) {
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getString(key);
    }

    public Dictionary setString(Args args) {
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        String value = args.get("value");
        return dictionary.setString(key, value);
    }

    public Object getObject(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getString(key);
    }

    public Dictionary setObject(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Object value = args.get("value");
        return  dictionary.setObject(key, value);
    }


    public Number getNumber(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getNumber(key);
    }

    public Dictionary setNumber(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Number value = args.get("value");
        return  dictionary.setObject(key, value);
    }


    public Integer getInt(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getInt(key);
    }

    public Dictionary setInt(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Integer value = args.get("value");
        return  dictionary.setObject(key, value);
    }


    public Long getLong(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getLong(key);
    }

    public Dictionary setLong(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Long value = args.get("value");
        return  dictionary.setLong(key, value);
    }


    public Float getFloat(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getFloat(key);
    }

    public Dictionary setFloat(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Float value = args.get("value");
        return  dictionary.setFloat(key, value);
    }


    public Double getDouble(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDouble(key);
    }

    public Dictionary setDouble(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Double value = args.get("value");
        return  dictionary.setObject(key, value);
    }


    public Boolean getBoolean(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getBoolean(key);
    }

    public Dictionary setBoolean(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Boolean value = args.get("value");
        return  dictionary.setBoolean(key, value);
    }


    public Blob getBlob(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getBlob(key);
    }

    public Dictionary setBlob(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Blob value = args.get("value");
        return  dictionary.setBlob(key, value);
    }


    public Date getDate(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDate(key);
    }

    public Dictionary setDate(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Date value = args.get("value");
        return  dictionary.setDate(key, value);
    }


    public Array getArray(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getArray(key);
    }

    public Dictionary setArray(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Array value = args.get("value");
        return  dictionary.setArray(key, value);
    }


    public Dictionary getDictionary(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDictionary(key);
    }

    public Dictionary setDictionary(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Dictionary value = args.get("value");
        return  dictionary.setDictionary(key, value);
    }

    public List<String> getKeys(Args args){
        Dictionary dictionary = args.get("dictionary");
        return dictionary.getKeys();
    }

    public Map<String, Object> toMap(Args args){
        Dictionary dictionary = args.get("dictionary");
        return dictionary.toMap();
    }

    public Dictionary remove(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.remove(key);
    }

    public boolean contains(Args args){
        Dictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.contains(key);
    }

    public Iterator<String> iterator(Args args){
        Dictionary dictionary = args.get("dictionary");
        return  dictionary.iterator();
    }
}
