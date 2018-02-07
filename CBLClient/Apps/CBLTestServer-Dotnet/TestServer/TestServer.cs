// 
//  TestServer.cs
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
using System.IO;
using System.Net;
using System.Threading;
using System.Threading.Tasks;

using JetBrains.Annotations;

namespace Couchbase.Lite.Testing
{
    public sealed class TestServer
    {
        #region Constants

        private const ushort Port = 55555;

        [NotNull]
        private static readonly Stream NullStream = new MemoryStream(new byte[0]);

        #endregion

        #region Variables

        private CancellationTokenSource _cancelSource;

        private HttpListener _httpListener;

        #endregion

        #region Public Methods

        public async Task Start()
        {
            Interlocked.Exchange(ref _httpListener, new HttpListener())?.Stop();
            Interlocked.Exchange(ref _cancelSource, new CancellationTokenSource())?.Cancel();

            _httpListener.Prefixes.Add($"http://*:{Port}/");
            _httpListener.Start();
            await Run();
        }

        public void Stop()
        {
            Interlocked.Exchange(ref _httpListener, null)?.Stop();
            Interlocked.Exchange(ref _cancelSource, null)?.Cancel();
        }

        #endregion

        #region Private Methods

        private async Task Run()
        {
            var cancelSource = _cancelSource;
            var httpListener = _httpListener;
            if (cancelSource == null || httpListener == null) {
                return;
            }

            while (!cancelSource.IsCancellationRequested) {
                var nextRequest = await httpListener.GetContextAsync().ConfigureAwait(false);
                if (nextRequest?.Request == null) {
                    Console.WriteLine("Weird error: null request, skipping...");
                    continue;
                }

                if (nextRequest.Request?.Url == null) {
                    Console.WriteLine("Weird error: null url, skipping...");
                    continue;
                }

                if (nextRequest.Request.HttpMethod != "POST") {
                    nextRequest.Response.WriteEmptyBody(HttpStatusCode.MethodNotAllowed);
                    continue;
                }

                Router.Handle(nextRequest.Request.Url, nextRequest.Request.InputStream ?? NullStream, nextRequest.Response);
            }
        }

        #endregion
    }
}
