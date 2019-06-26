package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import java.util.List;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Array;
import com.couchbase.lite.Dictionary;
import com.couchbase.lite.MutableArray;


public class ArrayRequestHandler {
    /* ------------ */
    /* -- Array --  */
    /* ------------ */

    public MutableArray create(Args args) {
        List<Object> array = args.get("content_array");
        if (array != null) {
            return new MutableArray(array);
        }
        return new MutableArray();
    }

    public String getString(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        return array.getString(index);
    }

    public MutableArray setString(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        String value = args.get("value");
        return array.setString(index, value);
    }

    public Array getArray(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        return array.getArray(index);
    }

    public MutableArray setArray(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        Array value = args.get("value");
        return array.setArray(index, value);
    }

    public Dictionary getDictionary(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        return array.getDictionary(index);
    }

    public MutableArray setDictionary(Args args) {
        MutableArray array = args.get("array");
        int index = args.get("key");
        Dictionary dictionary = args.get("dictionary");
        return array.setDictionary(index, dictionary);
    }

    public MutableArray addArray(Args args) {
        MutableArray array = args.get("array");
        Array value = args.get("value");
        return array.addArray(value);
    }

    public MutableArray addString(Args args) {
        MutableArray array = args.get("array");
        String value = args.get("value");
        return array.addString(value);
    }

    public MutableArray addDictionary(Args args) {
        MutableArray array = args.get("array");
        Dictionary value = args.get("value");
        return array.addDictionary(value);
    }
}


