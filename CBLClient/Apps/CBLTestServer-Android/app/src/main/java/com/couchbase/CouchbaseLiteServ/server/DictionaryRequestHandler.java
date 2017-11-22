package com.couchbase.CouchbaseLiteServ.server;


import java.util.HashMap;
import java.util.Map;

public class DictionaryRequestHandler{
    /* -------------- */
    /* - Dictionary - */
    /* -------------- */

    public Map dictionary_create(Args args) {
        return new HashMap();
    }

    public Object dictionary_get(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");

        return map.get(key);
    }

    public void dictionary_put(Args args) {
        Map<String, Object> map = args.get("dictionary");
        String key = args.get("key");
        String string = args.get("string");

        map.put(key, string);
    }
}
