using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using Couchbase.Lite.Sync;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

using Couchbase.Lite.Query;


namespace Couchbase.Lite.Testing
{
    internal static class CollatorMethods
    {
        public static void Ascii([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            bool ignoreCase = (bool) postBody["ignoreCase"];
            var collationID = Collation.ASCII().IgnoreCase(ignoreCase);
            response.WriteBody(collationID);

        }

        public static void Unicode([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            bool ignoreCase = (bool) postBody["ignoreCase"];
            bool ignoreAccents = (bool) postBody["ignoreAccents"];
            var collationID = Collation.Unicode().IgnoreCase(ignoreCase).IgnoreAccents(ignoreAccents);
            response.WriteBody(collationID);
        }
    }
}
