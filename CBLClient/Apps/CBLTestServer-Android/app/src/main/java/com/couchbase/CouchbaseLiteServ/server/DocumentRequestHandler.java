package com.couchbase.CouchbaseLiteServ.server;


import com.couchbase.lite.Blob;
import com.couchbase.lite.Dictionary;
import com.couchbase.lite.Document;
import com.couchbase.lite.DocumentChange;
import com.couchbase.lite.DocumentChangeListener;
import com.couchbase.lite.Array;

import java.util.List;
import java.util.Map;
import java.util.Date;


public class DocumentRequestHandler{
    /* ------------ */
    /* - Document - */
    /* ------------ */
    public Document create(Args args) {
        String id = args.get("id");
        Map<String, Object> dictionary = args.get("dictionary");

        if (id != null) {
            if (dictionary == null) {
                return new Document(id);
            } else {
                return new Document(id, dictionary);
            }
        } else {
            if (dictionary == null) {
                return new Document();
            } else {
                return new Document(dictionary);
            }
        }
    }

    public Object get(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");
        return map.get(key);
    }


    public int count(Args args){
        Document document = args.get("document");
        return document.count();
    }

    public Document set(Args args){
        Document document = args.get("document");
        Map<String, Object> dictionary  = args.get("dictionary");
        return document.set(dictionary);
    }

    public String getId(Args args) {
        Document document = args.get("document");
        return document.getId();
    }

    public String getString(Args args) {
        Document document = args.get("document");
        String key = args.get("key");
        return document.getString(key);
    }

    public Document setString(Args args) {
        Document document = args.get("document");
        String key = args.get("key");
        String value = args.get("value");
        return document.setString(key, value);
    }

    public Object getObject(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getString(key);
    }

    public Document setObject(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Object value = args.get("value");
        return  document.setObject(key, value);
    }


    public Number getNumber(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getNumber(key);
    }

    public Document setNumber(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Number value = args.get("value");
        return  document.setObject(key, value);
    }


    public Integer getInt(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getInt(key);
    }

    public Document setInt(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Integer value = args.get("value");
        return  document.setObject(key, value);
    }


    public Long getLong(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getLong(key);
    }

    public Document setLong(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Long value = args.get("value");
        return  document.setLong(key, value);
    }


    public Float getFloat(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getFloat(key);
    }

    public Document setFloat(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Float value = args.get("value");
        return  document.setFloat(key, value);
    }


    public Double getDouble(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getDouble(key);
    }

    public Document setDouble(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Double value = args.get("value");
        return  document.setObject(key, value);
    }


    public Boolean getBoolean(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getBoolean(key);
    }

    public Document setBoolean(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Boolean value = args.get("value");
        return  document.setBoolean(key, value);
    }


    public Blob getBlob(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getBlob(key);
    }

    public Document setBlob(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Blob value = args.get("value");
        return  document.setBlob(key, value);
    }


    public Date getDate(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getDate(key);
    }

    public Document setDate(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Date value = args.get("value");
        return  document.setDate(key, value);
    }


    public Array getArray(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getArray(key);
    }

    public Document setArray(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Array value = args.get("value");
        return  document.setArray(key, value);
    }


    public Dictionary getDictionary(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getDictionary(key);
    }

    public Document setDictionary(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        Dictionary value = args.get("value");
        return  document.setDictionary(key, value);
    }

    public List<String> getKeys(Args args){
        Document document = args.get("document");
        List<String> keys = document.getKeys();
        return keys;
    }

    public Map<String, Object> toMap(Args args){
        Document document = args.get("document");
        return document.toMap();
    }

    public Document removeKey(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.remove(key);
    }

    public boolean contains(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.contains(key);
    }
}

class MyDocumentChangeListener implements DocumentChangeListener {
    private List<DocumentChange> changes;

    public List<DocumentChange> getChanges(){
        return changes;
    }

    @Override
    public void changed(DocumentChange change) {
        changes.add(change);
    }
}


