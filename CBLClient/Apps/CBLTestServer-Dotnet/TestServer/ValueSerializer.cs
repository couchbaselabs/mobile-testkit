using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;

using JetBrains.Annotations;

using Newtonsoft.Json;

namespace Couchbase.Lite.Testing
{
    public class ValueSerializer
    {
        public static string Serialize(Object value, Type t)
        {
            if (value == null)
            {
                return "null";
            }
            else if (t.Equals(typeof(bool)))
            {
                Boolean item = Convert.ToBoolean(value);
                return item ? "true" : "false";
            }
            else if (t.Equals(typeof(string)) || t.Equals(typeof(Blob)))
            {
                return "\"" + value.ToString() + "\"";
            }
            else if (t.Equals(typeof(int)) || t.Equals(typeof(uint)))
            {
                return "I" + value;
            }
            else if (t.Equals(typeof(long)) || t.Equals(typeof(ulong)))
            {
                return "L" + value;
            }
            else if (t.Equals(typeof(float)) || t.Equals(typeof(double)))
            {
                return "F" + value;
            }
            else if ((value is IDictionary) || (value is IEnumerable<KeyValuePair<string, object>>))
            {
                Dictionary<string, object> dictionary = null;
                if (value is Couchbase.Lite.DictionaryObject)
                {
                    Couchbase.Lite.DictionaryObject newval = (Couchbase.Lite.DictionaryObject)value;
                    dictionary = newval.ToDictionary();
                }
                else
                {
                    dictionary = (Dictionary<string, object>)value;
                }

                Dictionary<string, string> stringMap = new Dictionary<string, string>();
                foreach (string key in dictionary.Keys)
                {
                    stringMap.Add(key, Serialize(dictionary[key], dictionary[key]?.GetType()));
                }
                return JsonConvert.SerializeObject(stringMap);
            }
            else if (value is IList list)
            {
                List<string> stringList = new List<string>();

                foreach (var item in list)
                {
                    stringList.Add(Serialize(item, item.GetType()));
                }
                return JsonConvert.SerializeObject(stringList);
            }
            else
            {
                Console.WriteLine("Type of Value is " + t.ToString());
                return value.ToString();
            }
        }

        public static Dictionary<string, object> Deserialize(IReadOnlyDictionary<string, string> jsonObj)
        {
            Dictionary<string, object> bodyObj = new Dictionary<string, object>();

            foreach (string key in jsonObj.Keys)
            {
                string value = jsonObj[key];
                bodyObj.Add(key, DeserializeValue(value));
            }
            return bodyObj;
        }

        internal static object DeserializeValue(String value)
        {
            if (value == "null")
            {
                return null;
            }
            else if (value.Equals("true"))
            {
                return true;
            }
            else if (value.Equals("false"))
            {
                return false;
            }
            else if (value.StartsWith("\"") && value.EndsWith("\""))
            {
                return value.Replace("\"", String.Empty);
            }
            else if (value.StartsWith("{"))
            {
                var dictJsonObj = JsonConvert.DeserializeObject<Dictionary<string, string>>(value);
                Dictionary<string, object> dictObj = new Dictionary<string, object>();

                foreach (string key in dictJsonObj.Keys)
                {
                    object obj = DeserializeValue(dictJsonObj[key].ToString());
                    dictObj.Add(key, obj);
                }
                return dictObj;
            }
            else if (value.StartsWith("["))
            {
                var listJsonObj = JsonConvert.DeserializeObject<List<string>>(value);
                List<object> list = new List<object>();

                foreach (string item in listJsonObj)
                {
                    object obj = DeserializeValue(item);
                    list.Add(obj);
                }
                return list;
            }
            else if (value.StartsWith("I"))
            {
                return int.Parse(value.Substring(1));
            }
            else if (value.StartsWith("F"))
            {
                return float.Parse(value.Substring(1));
            }
            else if (value.StartsWith("D"))
            {
                return double.Parse(value.Substring(1));
            }
            else if (value.StartsWith("L"))
            {
                return long.Parse(value.Substring(1));
            }
            else
            {
                throw new Exception("Invalid value type");
            }

        }
    }

}
