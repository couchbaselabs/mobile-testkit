package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Blob;
import com.couchbase.lite.Document;
import com.couchbase.lite.MutableDictionary;
import com.couchbase.lite.DocumentChange;
import com.couchbase.lite.DocumentChangeListener;
import com.couchbase.lite.Array;
import com.couchbase.lite.MutableDocument;

import java.util.List;
import java.util.Map;
import java.util.Date;

public class DocumentRequestHandler{
    /* ------------ */
    /* - Document - */
    /* ------------ */
    public MutableDocument create(Args args) {
        String id = args.get("id");
        Map<String, Object> dictionary = args.get("dictionary");

        if (id != null) {
            if (dictionary == null) {
                return new MutableDocument(id);
            } else {
                return new MutableDocument(id, dictionary);
            }
        } else {
            if (dictionary == null) {
                return new MutableDocument();
            } else {
                return new MutableDocument(dictionary);
            }
        }
    }

    public Object get(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");
        return map.get(key);
    }


    public int count(Args args){
        MutableDocument document = args.get("document");
        return document.count();
    }

//    Not available in DB21
//    public MutableDocument set(Args args){
//        MutableDocument document = args.get("document");
//        Map<String, Object> dictionary  = args.get("dictionary");
//        return document.set(dictionary);
//    }

    public String getId(Args args) {
        Document document = args.get("document");
        return document.getId();
    }

    public String getString(Args args) {
        Document document = args.get("document");
        String key = args.get("key");
        return document.getString(key);
    }

    public MutableDocument setString(Args args) {
        MutableDocument document = args.get("document");
        String key = args.get("key");
        String value = args.get("value");
        return document.setString(key, value);
    }

//    Not available in DB21
//    public Object getObject(Args args){
//        MutableDocument document = args.get("document");
//        String key = args.get("key");
//        return document.getObject(key);
//    }
//
//    public MutableDocument setObject(Args args){
//        MutableDocument document = args.get("document");
//        String key = args.get("key");
//        Object value = args.get("value");
//        return  document.setObject(key, value);
//    }


    public Number getNumber(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getNumber(key);
    }

    public MutableDocument setNumber(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Number value = args.get("value");
        return  document.setNumber(key, value);
    }


    public Integer getInt(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getInt(key);
    }

    public MutableDocument setInt(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Integer value = args.get("value");
        return  document.setInt(key, value);
    }


    public Long getLong(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getLong(key);
    }

    public MutableDocument setLong(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Long value = args.get("value");
        return  document.setLong(key, value);
    }


    public Float getFloat(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getFloat(key);
    }

    public MutableDocument setFloat(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Float value = args.get("value");
        return  document.setFloat(key, value);
    }


    public Double getDouble(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getDouble(key);
    }

    public MutableDocument setDouble(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Double value = args.get("value");
        return  document.setDouble(key, value);
    }

    public Boolean getBoolean(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getBoolean(key);
    }

    public MutableDocument setBoolean(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Boolean value = args.get("value");
        return  document.setBoolean(key, value);
    }


    public Blob getBlob(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getBlob(key);
    }

    public MutableDocument setBlob(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Blob value = args.get("value");
        return  document.setBlob(key, value);
    }


    public Date getDate(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getDate(key);
    }

    public MutableDocument setDate(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        Date value = args.get("value");
        return  document.setDate(key, value);
    }


    public List getArray(Args args){
        Document document = args.get("document");
        String key = args.get("key");
        return document.getArray(key).toList();
    }

//    public MutableDocument setArray(Args args){
//        MutableDocument document = args.get("document");
//        String key = args.get("key");
//        List<Object> list = args.get("value");
//        Array value = new Array(list);
//        return  document.setArray(key, value);
//    }


    public MutableDictionary getDictionary(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.getDictionary(key);
    }

    public MutableDocument setDictionary(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        MutableDictionary value = args.get("value");
        return  document.setDictionary(key, value);
    }

    public List<String> getKeys(Args args){
        Document document = args.get("document");
        return document.getKeys();
    }

    public Map<String, Object> toMap(Args args){
        MutableDocument document = args.get("document");
        return document.toMap();
    }

    public MutableDocument removeKey(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.remove(key);
    }

    public boolean contains(Args args){
        MutableDocument document = args.get("document");
        String key = args.get("key");
        return document.contains(key);
    }

    public String documentChange_getDocumentId(Args args){
        DocumentChange change = args.get("change");
        return change.getDocumentID();
    }

    public String documentChange_toString(Args args){
        DocumentChange change = args.get("change");
        return change.toString();
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


