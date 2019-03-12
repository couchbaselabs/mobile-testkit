// 
//  DocumentMethods.cs
// 
//  Author:
//   Jim Borden  <jim.borden@couchbase.com>
// 
//  Copyright (c) 2017 Couchbase, Inc All rights reserved.
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

using JetBrains.Annotations;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class DocumentMethods
    {
        #region Public Methods

        public static void DocumentCreate([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var hasDictionary = postBody.ContainsKey("dictionary");

            if (postBody.ContainsKey("id"))
            {
                var id = postBody["id"];
                if (hasDictionary)
                {
                    response.WriteBody(MemoryMap.New<MutableDocument>(id, postBody["dictionary"]));
                }
                else
                {
                    response.WriteBody(MemoryMap.New<MutableDocument>(id));
                }
            }
            else
            {
                if (hasDictionary)
                {
                    response.WriteBody(MemoryMap.New<MutableDocument>(postBody["dictionary"]));
                }
                else
                {
                    response.WriteBody(MemoryMap.New<MutableDocument>());
                }
            }
        }


        public static void DocumentCount([NotNull] NameValueCollection args,
                                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                                          [NotNull] HttpListenerResponse response)
        {
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.Count));
        }

        public static void DocumentGetString([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<Document>(postBody, "document", doc => response.WriteBody(doc.GetString(key)));
        }

        public static void DocumentSetString([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = postBody["value"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetString(key, val))));
        }

        public static void DocumentGetInt([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetInt(key)));
        }

        public static void DocumentSetInt([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (int)postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetInt(key, val))));
        }

        public static void DocumentGetLong([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetLong(key)));
        }

        public static void DocumentSetLong([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (long)postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetLong(key, val))));
        }

        public static void DocumentGetFloat([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetFloat(key)));
        }

        public static void DocumentSetFloat([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (float)postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetFloat(key, val))));
        }

        public static void DocumentGetDouble([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetDouble(key)));
        }

        public static void DocumentSetDouble([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = Convert.ToDouble(postBody["value"]);
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetDouble(key, val))));
        }

        public static void DocumentGetBoolean([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetBoolean(key)));
        }

        public static void DocumentSetBoolean([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (bool)postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetBoolean(key, val))));
        }

        public static void DocumentGetBlob([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.GetBlob(key)));
        }

        public static void DocumentSetBlob([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = (Blob)postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.SetBlob(key, val)));
        }

        public static void DocumentGetArray([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var doc = MemoryMap.Get<Document>(postBody["document"].ToString());
            response.WriteBody(MemoryMap.Store(doc.GetArray(key)));
        }

        public static void DocumentSetArray([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = MemoryMap.Get<ArrayObject>(postBody["value"].ToString());
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetArray(key, val))));
        }

        public static void DocumentGetDate([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.GetDate(key).DateTime)));
        }

        public static void DocumentSetDate([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = postBody["value"].ToString();
            var dateVal = MemoryMap.Get<DateTime>(val);
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetDate(key, dateVal))));
        }

        public static void DocumentSetData([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var val = (Dictionary<string, Object>)postBody["data"];
            MutableDocument doc = MemoryMap.Get<MutableDocument>(postBody["document"].ToString());
            response.WriteBody(MemoryMap.Store(doc.SetData(val)));
        }

        public static void DocumentGetDictionary([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<Document>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.GetDictionary(key))));
        }

        public static void DocumentSetDictionary([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<DictionaryObject>(postBody, "value", dict =>
            {
                With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetDictionary(key, dict))));
            });
        }

        public static void DocumentGetKeys([NotNull] NameValueCollection args,
                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                  [NotNull] HttpListenerResponse response)
        {
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.Keys));
        }

        public static void DocumentToDictionary([NotNull] NameValueCollection args,
                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                  [NotNull] HttpListenerResponse response)
        {
            With<Document>(postBody, "document", doc => response.WriteBody(doc.ToDictionary()));
        }

        public static void DocumentToMutable([NotNull] NameValueCollection args,
                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                  [NotNull] HttpListenerResponse response)
        {
            With<Document>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.ToMutable())));
        }

        public static void DocumentRemoveKey([NotNull] NameValueCollection args,
                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                          [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.Remove(key))));
        }

        public static void DocumentContains([NotNull] NameValueCollection args,
                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(doc.Contains(key)));
        }

        public static void DocumentDelete([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => With<Document>(postBody, "document", db.Delete));
            response.WriteEmptyBody();
        }

        public static void DocumentGetId([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Document>(postBody, "document", doc => response.WriteBody(doc.Id));
        }

        public static void DocumentGetValue([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            With<Document>(postBody, "document", doc => response.WriteBody(doc.GetValue(key)));
        }

        public static void DocumentSetValue([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            var key = postBody["key"].ToString();
            var val = postBody["value"];
            With<MutableDocument>(postBody, "document", doc => response.WriteBody(MemoryMap.Store(doc.SetValue(key, val))));
        }
        #endregion
    }
}