using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using JetBrains.Annotations;
using static Couchbase.Lite.MutableArrayObject;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class ArrayMethods
    {
        public static void ArrayCreate([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            string arrayId = null;
            if (postBody.ContainsKey("content_array")) {
                List<Object> array = (List<Object>)postBody["content_array"];
                arrayId = MemoryMap.New<MutableArrayObject>(array);
            } else
            {
                arrayId = MemoryMap.New<MutableArrayObject>();
            }
            response.WriteBody(arrayId);
        }

        public static void ArrayGetString([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.GetString(key)));
        }

        public static void ArraySetString([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            var val = postBody["value"].ToString();
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.SetString(key, val)));  
        }

        public static void ArrayGetArray([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.GetArray(key)));
        }

        public static void ArraySetArray([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            var val = (ArrayObject)postBody["value"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.SetArray(key, val)));
        }

        public static void ArrayGetDictionary([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.GetDictionary(key)));
        }

        public static void ArraySetDictionary([NotNull] NameValueCollection args,
                                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                                 [NotNull] HttpListenerResponse response)
        {
            var key = (int)postBody["key"];
            var val = (DictionaryObject)postBody["dictionary"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.SetDictionary(key, val)));
        }

        public static void ArrayAddDictionary([NotNull] NameValueCollection args,
                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                         [NotNull] HttpListenerResponse response)
        {
            var val = MemoryMap.Get<DictionaryObject>(postBody["value"].ToString());
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(MemoryMap.Store(a.AddDictionary(val))));
        }

        public static void ArrayAddArray([NotNull] NameValueCollection args,
                 [NotNull] IReadOnlyDictionary<string, object> postBody,
                 [NotNull] HttpListenerResponse response)
        {
            var val = (ArrayObject)postBody["value"];
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(a.AddArray(val)));
        }

        public static void ArrayAddString([NotNull] NameValueCollection args,
         [NotNull] IReadOnlyDictionary<string, object> postBody,
         [NotNull] HttpListenerResponse response)
        {
            var val = postBody["value"].ToString();
            With<MutableArrayObject>(postBody, "array", a => response.WriteBody(MemoryMap.Store(a.AddString(val))));
        }
    }
}
