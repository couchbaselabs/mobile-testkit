// 
//  BasicAuthenticationMethods.cs
// 
//  Author:
//   Prasanna Gholap <Prasanna.Gholap@couchbase.com>
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
// 
//  http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// 

using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using Couchbase.Lite.Sync;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using Newtonsoft.Json.Linq;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class BasicAuthenticationMethods
    {
        public static void Create([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var username = postBody["username"].ToString();
            var password = postBody["password"].ToString();
            var authenticator = MemoryMap.New<BasicAuthenticator>(username, password);
            response.WriteBody(authenticator);
        }

        public static void GetPassword([NotNull] NameValueCollection args,
                                       [NotNull] IReadOnlyDictionary<string, object> postBody,
                                       [NotNull] HttpListenerResponse response)
        {
            With<BasicAuthenticator>(postBody, "authenticator", au => response.WriteBody(au.Password));
        }
        public static void GetUsername([NotNull] NameValueCollection args,
                               [NotNull] IReadOnlyDictionary<string, object> postBody,
                               [NotNull] HttpListenerResponse response)
        {
            With<BasicAuthenticator>(postBody, "authenticator", au => response.WriteBody(au.Username));
        }
    }
}