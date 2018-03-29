using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Globalization;
using System.Net;

using JetBrains.Annotations;
using static Couchbase.Lite.MutableArrayObject;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class DataTypeMethods
    {
        public static void DataTypeSetLong([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {    
            var val = (long)postBody["value"];
            response.WriteBody(val);
        }

        public static void DataTypeSetDouble([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            var val = (float)(postBody["value"]);
            //val = (double)val;
            response.WriteBody(val);
        }

        public static void DataTypeCompare([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            var first = postBody["first"].ToString();
            var second = postBody["second"].ToString();
            response.WriteBody(first == second);
        }

        public static void DataTypeCompareLong([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            var first = (double)postBody["first"];
            var second = (double)postBody["second"];
            response.WriteBody(first == second);
        }

        public static void DataTypeSetDate([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            response.WriteBody(MemoryMap.Store(DateTime.Now));
        }

        public static void DataTypeCompareDate([NotNull] NameValueCollection args,
                                            [NotNull] IReadOnlyDictionary<string, object> postBody,
                                            [NotNull] HttpListenerResponse response)
        {
            var date1 = MemoryMap.Get<DateTime>(postBody["date1"].ToString());
            var date2 = MemoryMap.Get<DateTime>(postBody["date2"].ToString());

            if (date1 == date2) {
                response.WriteBody(true);
            }
            else
            {
                response.WriteBody(false);
            }
            
        }
    }
}
