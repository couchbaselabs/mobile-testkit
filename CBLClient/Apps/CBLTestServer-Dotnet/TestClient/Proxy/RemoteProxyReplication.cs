// 
//  RemoteProxyReplication.cs
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
using System.Threading.Tasks;

using JetBrains.Annotations;

using RestEase;

namespace TestClient
{
    public sealed class RemoteProxyReplication : RemoteProxyObject
    {
        #region Constants

        [NotNull]
        private static readonly IReplicationRESTApi Api = RestClient.For<IReplicationRESTApi>(Program.ServerUrl) 
                                                          ?? throw new ApplicationException("Unable to create the replication REST API");

        #endregion

        #region Variables

        public readonly IDictionary<string, object> Authentication = new Dictionary<string, object>();

        #endregion

        #region Constructors

        public RemoteProxyReplication(RemoteProxyDatabase sourceDb, string targetUrl, bool continuous = false,
            string replicationType = "pushandpull", IDictionary<string, object> authentication = null)
            : base(Api.ConfigureAsync(sourceDb, targetUrl, continuous, replicationType, new Dictionary<string, object> { ["auth"] = authentication }).Result)
        {

        }

        #endregion

        #region Public Methods

        public static IDictionary<string, object> BasicAuthentication(string username, string password)
        {
            return new Dictionary<string, object>
            {
                ["type"] = "basic",
                ["username"] = username,
                ["password"] = password
            };
        }

        public static IDictionary<string, object> SessionAuthentication(string sessionId, DateTimeOffset? expires)
        {
            var retVal = new Dictionary<string, object>
            {
                ["type"] = "session",
                ["session"] = sessionId
            };

            if (expires.HasValue) {
                retVal["expires"] = expires.Value;
            }

            return retVal;
        }

        [NotNull]
        [ItemNotNull]
        public Task<IReadOnlyDictionary<string, object>> GetStatusAsync() => Api.GetStatusAsync(this);

        [NotNull]
        public Task StartAsync() => Api.StartAsync(this);

        [NotNull]
        public Task StopAsync() => Api.StopAsync(this);

        #endregion

        #region Overrides

        protected override IObjectRESTApi GetApi() => Api;

        #endregion
    }
}