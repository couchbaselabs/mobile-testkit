using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using JetBrains.Annotations;
using Couchbase.Lite;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class DataSourceMethods
    {
        public static void Database([NotNull] NameValueCollection args,
                                    [NotNull] IReadOnlyDictionary<string, object> postBody,
                                    [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => response.WriteEmptyBody()); 
        }
    }
}
