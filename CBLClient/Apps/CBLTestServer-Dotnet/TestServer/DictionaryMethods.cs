using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using JetBrains.Annotations;
using static Couchbase.Lite.MutableDictionaryObject;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class DictionaryMethods
    {
        public static void DictionaryCreate([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
			string dictId = null;
            if (postBody.ContainsKey("content_dict"))
            {
                Dictionary<String, Object> dictionary = (Dictionary<String, Object>)postBody["content_dict"];
                dictId = MemoryMap.New<MutableDictionaryObject>(dictionary);
            }
            else
            {
                dictId = MemoryMap.New<MutableDictionaryObject>();
            }
            response.WriteBody(dictId);
        }

        public static void DictionaryCount([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            With<MutableDictionaryObject>(postBody, "dictionary", dict => response.WriteBody(dict.Count));
        }

        public static void DictionaryGetString([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetString(key)));
        }

        public static void DictionarySetString([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = postBody["value"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetString(key, val)));  
        }

        public static void DictionaryGetInt([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetInt(key)));
        }

        public static void DictionarySetInt([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (int) postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetInt(key, val)));
        }

        public static void DictionaryGetLong([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetLong(key)));
        }

        public static void DictionarySetLong([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (long)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetLong(key, val)));
        }

        public static void DictionaryGetFloat([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetFloat(key)));
        }

        public static void DictionarySetFloat([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (float)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetFloat(key, val)));
        }

        public static void DictionaryGetDouble([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetDouble(key)));
        }

        public static void DictionarySetDouble([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (double)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetDouble(key, val)));
        }

        public static void DictionaryGetBoolean([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetBoolean(key)));
        }

        public static void DictionarySetBoolean([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (bool)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetBoolean(key, val)));
        }

        public static void DictionaryGetBlob([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetBlob(key)));
        }

        public static void DictionarySetBlob([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (Blob)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetBlob(key, val)));
        }

        public static void DictionaryGetDate([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetDate(key)));
        }

        public static void DictionarySetDate([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (DateTimeOffset)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetDate(key, val)));
        }

        public static void DictionaryGetArray([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetArray(key)));
        }

        public static void DictionarySetArray([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (ArrayObject)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetArray(key, val)));
        }

        public static void DictionaryGetDictionary([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetDictionary(key)));
        }

        public static void DictionarySetDictionary([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (DictionaryObject)postBody["value"];
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetDictionary(key, val)));
        }

        public static void DictionaryGetKeys([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.Keys));
        }

        public static void DictionaryRemove([NotNull] NameValueCollection args,
                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                 [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.Remove(key)));
        }

        public static void DictionaryContains([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.Contains(key)));
        }

        public static void DictionarySetValue([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = postBody["value"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.SetValue(key, val)));
        }

        public static void DictionaryGetValue([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.GetValue(key)));
        }

        public static void DictionaryToMap([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            With<MutableDictionaryObject>(postBody, "dictionary", d => response.WriteBody(d.ToDictionary()));
        }
    }
}
