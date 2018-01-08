package com.couchbase.CouchbaseLiteServ.server;

import com.google.gson.Gson;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ValueSerializer {

    public static String serialize(Object value, Memory memory) {
        if (value == null)  {
            return null;
        } else if (value instanceof Boolean) {
            Boolean bool = (Boolean) value;

            return (bool ? "true" : "false");
        } else if (value instanceof Integer) {
            Integer number = (Integer) value;

            return "I" + number.toString();
        } else if (value instanceof Long) {
            Long number = (Long) value;

            return "L" + number.toString();
        } else if (value instanceof Float) {
            Float number = (Float) value;

            return "F" + number.toString();
        } else if (value instanceof Map) {
            Map<String, Object> map = (Map<String, Object>)value;
            Map<String, String> stringMap = new HashMap<>();

            for (Map.Entry<String, Object> entry : map.entrySet()) {
                String key = entry.getKey();
                String string = serialize(entry.getValue(), memory);
                stringMap.put(key, string);
            }
            return new Gson().toJson(stringMap);
        } else if (value instanceof List) {
            List list = (List)value;
            List<String> stringList = new ArrayList<>();

            for (Object object : list) {
                String string = serialize(object, memory);
                stringList.add(string);
            }
            return new Gson().toJson(stringList);
        } else if (value instanceof String) {
            String string = (String) value;
            return "\"" + string + "\"";
        } else {
            return memory.add(value);
        }
    }

    public static <T> T deserialize(String value, Memory memory) {
        if ((value == null) || (value == "null")) {
            return null;
        } else if (value.startsWith("@")) {
            return memory.get(value);
        } else if (value.equals("true")) {
            return (T)Boolean.TRUE;
        } else if (value.equals("false")) {
            return (T)Boolean.FALSE;
        } else if (value.startsWith("{")) {
            Map<String, String> stringMap = new Gson().fromJson(value, Map.class);
            Map<String, Object> map = new HashMap<>();

            for (Map.Entry<String, String> entry : stringMap.entrySet()) {
                String key = entry.getKey();
                String nestedVal;
                String val = entry.getValue();
//                if (val.startsWith("\"")){
//                    nestedVal = val.substring(1, value.length() - 1);
//                } else {
//                    nestedVal = val;
//                }
                Object object = deserialize(val, memory);

                map.put(key, object);
            }

            return (T)map;
        } else if (value.startsWith("[")) {
            List<String> stringList = new Gson().fromJson(value, List.class);
            List list = new ArrayList<>();

            for (String string : stringList) {
                Object object = deserialize(string, memory);

                list.add(object);
            }

            return (T)list;
        } else if (value.startsWith("\"") && value.endsWith("\"")) {
            return (T)value.substring(1, value.length() - 1);
        } else if (value.startsWith("I")){
            return (T) new Integer(value.substring(1));
        } else if (value.startsWith("L")){
            return (T) new Long(value.substring(1));
        } else if (value.startsWith("F")){
            return (T) new Float(value.substring(1));
        } else if (value.startsWith("D")){
            return (T) new Double(value.substring(1));
        }
        else {
            throw new IllegalArgumentException("Invalid value type" + (String) value);
        }
    }
}
