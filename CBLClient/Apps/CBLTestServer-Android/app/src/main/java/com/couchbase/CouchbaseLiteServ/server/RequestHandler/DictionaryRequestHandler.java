package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Array;
import com.couchbase.lite.Blob;
import com.couchbase.lite.Dictionary;
import com.couchbase.lite.MutableDictionary;
import com.couchbase.litecore.fleece.FLEncoder;

import java.util.Date;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

public class DictionaryRequestHandler{
    /* -------------- */
    /* - Dictionary - */
    /* -------------- */

    public MutableDictionary create(Args args) {
        Map<String, Object> dictionary = args.get("content_dict");
        if (dictionary != null){
            return new MutableDictionary(dictionary);
        }
        return new MutableDictionary();
    }

    public MutableDictionary toMutableDictionary(Args args) {
        Map<String, Object> dictionary = args.get("dictionary");
        MutableDictionary mutableDictionary = new MutableDictionary(dictionary);
        return mutableDictionary;
    }

    public int count(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        return dictionary.count();
    }

    public void fleeceEncode(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        FLEncoder encoder = args.get("encoder");
        dictionary.encodeTo(encoder);
    }

    public String getString(Args args) {
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getString(key);
    }

    public MutableDictionary setString(Args args) {
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        String value = args.get("value");
        return dictionary.setString(key, value);
    }


    public Number getNumber(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getNumber(key);
    }

    public MutableDictionary setNumber(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Number value = args.get("value");
        return  dictionary.setNumber(key, value);
    }


    public Integer getInt(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getInt(key);
    }

    public MutableDictionary setInt(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Integer value = args.get("value");
        return  dictionary.setInt(key, value);
    }


    public Long getLong(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getLong(key);
    }

    public MutableDictionary setLong(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Long value = args.get("value");
        return  dictionary.setLong(key, value);
    }


    public Float getFloat(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getFloat(key);
    }

    public MutableDictionary setFloat(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Double valDouble = args.get("value");
        Float value = valDouble.floatValue();
        return  dictionary.setFloat(key, value);
    }


    public Double getDouble(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDouble(key);
    }

    public MutableDictionary setDouble(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Double value = Double.valueOf(args.get("value").toString());
        return  dictionary.setDouble(key, value);
    }


    public Boolean getBoolean(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getBoolean(key);
    }

    public MutableDictionary setBoolean(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Boolean value = args.get("value");
        return  dictionary.setBoolean(key, value);
    }


    public Blob getBlob(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getBlob(key);
    }

    public MutableDictionary setBlob(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Blob value = args.get("value");
        return  dictionary.setBlob(key, value);
    }


    public Date getDate(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDate(key);
    }

    public MutableDictionary setDate(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Date value = args.get("value");
        return  dictionary.setDate(key, value);
    }


    public Array getArray(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getArray(key);
    }

    public MutableDictionary setArray(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Array value = args.get("value");
        return  dictionary.setArray(key, value);
    }


    public MutableDictionary getDictionary(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getDictionary(key);
    }

    public MutableDictionary setDictionary(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Dictionary value = args.get("value");
        return  dictionary.setDictionary(key, value);
    }

    public Object getValue(Args args) {
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.getValue(key);
    }

    public MutableDictionary setValue(Args args) {
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        Object value = args.get("value");
        return dictionary.setValue(key, value);
    }

    public List<String> getKeys(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        return dictionary.getKeys();
    }

    public Map<String, Object> toMap(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        return dictionary.toMap();
    }

    public MutableDictionary remove(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.remove(key);
    }

    public boolean contains(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        String key = args.get("key");
        return dictionary.contains(key);
    }

    public Iterator<String> iterator(Args args){
        MutableDictionary dictionary = args.get("dictionary");
        return  dictionary.iterator();
    }
}
