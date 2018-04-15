using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using JetBrains.Annotations;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class EncryptionKeyMethods
    {
        //public static void EncryptionCreate([NotNull] NameValueCollection args,
        //                                    [NotNull] IReadOnlyDictionary<string, object> postBody,
        //                                    [NotNull] HttpListenerResponse response)
        //{
        //    var key = (byte[])postBody["key"];
        //    var password = postBody["password"].ToString();

        //    if (password != null){
        //        response.WriteBody(MemoryMap.New<EncryptionKey>(password));
        //    }
        //    else if (key != null){
        //        response.WriteBody(MemoryMap.New<EncryptionKey>(key));
        //    }
        //    else{
        //        throw new ArgumentException("Wrong Argument");
        //    }
        //}
    }
}
