// 
//  Program.cs
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
using System.IO;
using System.Threading;

using HandlerAction = System.Action<System.Collections.Specialized.NameValueCollection, 
    System.Collections.Generic.IReadOnlyDictionary<string, object>, 
    System.Net.HttpListenerResponse>;

namespace Couchbase.Lite.Testing.NetCore
{
    class Program
    {
        #region Private Methods

        private static void Extend()
        {
            Router.Extend(new Dictionary<string, HandlerAction>
            {
                ["start_sync_gateway"] = OrchestrationMethods.StartSyncGateway,
                ["kill_sync_gateway"] = OrchestrationMethods.KillSyncGateway,
                //["compile_query"] = QueryMethods.CompileQuery,
                ["start_cb_server"] = OrchestrationMethods.StartCouchbaseServer,
                ["stop_cb_server"] = OrchestrationMethods.StopCouchbaseServer
            });
        }

        static void Main(string[] args)
        {
            Couchbase.Lite.Support.NetDesktop.Activate();
            Extend();

            Database.Log.Console.Level = Logging.LogLevel.Debug;
            Database.Log.Console.Domains = Logging.LogDomain.All;
            var logPath = Path.Combine(Directory.GetCurrentDirectory(), "LogTestLogs");
            Directory.CreateDirectory(logPath);
            Console.WriteLine("Logs are available at - \"{0}\"", logPath);
            DatabaseConfiguration config = new DatabaseConfiguration();
            Console.WriteLine("Default directory for database creation is - \"{0}\"", config.Directory.ToString());
            Database.Log.File.UsePlaintext = true;
            Database.Log.File.Directory = logPath;
            Database.Log.File.MaxRotateCount = 0;

            TestServer.FilePathResolver = path => path;
            var listener = new TestServer();
            listener.Start();

            Console.WriteLine("CBLTestServer-NetCore - Press any Ctrl+C to exit...");
            var wait = new ManualResetEventSlim();
            Console.CancelKeyPress += (sender, e) =>
            {
                wait.Set();
            };

            wait.Wait();

            listener.Stop();
        }

        #endregion
    }
}
