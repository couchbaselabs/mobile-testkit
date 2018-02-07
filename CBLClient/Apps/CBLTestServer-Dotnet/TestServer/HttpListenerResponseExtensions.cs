// 
//  HttpListenerResponseExtensions.cs
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
using System.Net;
using System.Text;

using JetBrains.Annotations;

using Newtonsoft.Json;

namespace Couchbase.Lite.Testing
{
    public static class HttpListenerResponseExtensions
    {
        public static void WriteBody<T>([NotNull]this HttpListenerResponse response, T bodyObj, bool success = true)
        {
            if (response.OutputStream == null)
            {
                throw new InvalidOperationException("Cannot write to a response with a null OutputStream");
            }
            Type bodyObjType = bodyObj.GetType();
            var postBody = JsonConvert.SerializeObject(bodyObj);
            var serializedBody = ValueSerializer.Serialize(bodyObj, bodyObjType);
            var body = Encoding.UTF8.GetBytes(serializedBody);
            response.ContentType = "application/json";
            response.ContentLength64 = body.LongLength;
            response.ContentEncoding = Encoding.UTF8;
            response.StatusCode = success ? (int)HttpStatusCode.OK : (int)HttpStatusCode.BadRequest;
            response.OutputStream.Write(body, 0, body.Length);
            response.Close();
        }

        public static void WriteRawBody([NotNull]this HttpListenerResponse response, string bodyStr, bool success = true)
        {
            if (response.OutputStream == null)
            {
                throw new InvalidOperationException("Cannot write to a response with a null OutputStream");
            }

            var body = Encoding.UTF8.GetBytes(bodyStr);
            response.ContentType = "application/json";
            response.ContentLength64 = body.LongLength;
            response.ContentEncoding = Encoding.UTF8;
            response.StatusCode = success ? (int)HttpStatusCode.OK : (int)HttpStatusCode.BadRequest;
            response.OutputStream.Write(body, 0, body.Length);
            response.Close();
        }

        public static void WriteEmptyBody([NotNull]this HttpListenerResponse response, HttpStatusCode code = HttpStatusCode.OK)
        {

            response.ContentLength64 = 0;
            response.StatusCode = (int)code;

            response.Close();
        }
    }
}