package com.couchbase.CouchbaseLiteServ.server;

import android.util.Log;

public class ValueSerializer {

    public static String serialize(Object value, Memory memory) {
        if (value == null)  {
            return "null";
        } else if (value instanceof String) {
            String string = (String) value;

            return "\"" + string + "\"";
        } else if (value instanceof Number) {
            Number number = (Number) value;

            return number.toString();
        } else if (value instanceof Boolean) {
            Boolean bool = (Boolean) value;

            return (bool ? "true" : "false");
        } else {
            return memory.add(value);
        }
    }

    public static <T> T deserialize(String value, Memory memory) {
        if (value == null) {
            return null;
        } else if (value.startsWith("@")) {
            return memory.get(value);
        } else if (value.equals("true")) {
            return (T)Boolean.TRUE;
        } else if (value.equals("false")) {
            return (T)Boolean.FALSE;
        } else if (value.startsWith("\"") && value.endsWith("\"")) {
            return (T)value.substring(1, value.length() - 1);
        } else {
            if (value.contains(".")) {
                return (T)new Double(value);
            } else {
                return (T)new Integer(value);
            }
        }
    }
}
