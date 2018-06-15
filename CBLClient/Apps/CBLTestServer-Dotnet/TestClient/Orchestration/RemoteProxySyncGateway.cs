// 
//  RemoteProxySyncGateway.cs
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
using System.Globalization;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text.RegularExpressions;

using Couchbase.Lite.Sync;

using JetBrains.Annotations;

using RestEase;

namespace TestClient.Orchestration
{
    public sealed class RemoteProxySyncGateway : RemoteProxyObject
    {
        #region Constants

        [NotNull] 
        private static readonly IOrchestrationRESTApi OrchestrationApi =
            RestClient.For<IOrchestrationRESTApi>(Program.SyncGatewayOrchestrationUrl)
            ?? throw new ApplicationException("Unable to create Orchestration REST API");

        #endregion

        #region Variables

        [NotNull]
        private readonly SyncGateway _syncGateway;

        [NotNull]
        private readonly Uri _replicationUrl;

        #endregion

        #region Constructors

        public RemoteProxySyncGateway(string path, string config)
            : base(OrchestrationApi.StartSyncGatewayAsync(path, new Dictionary<string, object> { ["config"] = config }).Result)
        {

            var publicPort = ParsePort(FindKeyValue(config, "interface"), 4984);
            var adminPort = ParsePort(FindKeyValue(config, "adminInterface"), 4985);
            var ipAddr = new Uri(Program.SyncGatewayOrchestrationUrl).Authority.Split(':').First();
            var secure = FindKeyValue(config, "SSLCert") != null && FindKeyValue(config, "SSLKey") != null;
            var scheme = secure ? "https" : "http";
            var baseUrl = new Uri($"{scheme}://{ipAddr}");
            _syncGateway = new SyncGateway(baseUrl, publicPort, adminPort);
            _replicationUrl = CreateReplicationUrl(baseUrl, secure, publicPort);
        }

        [NotNull]
        private Uri CreateReplicationUrl([NotNull]Uri baseUrl, bool secure, int publicPort)
        {
            var scheme = secure ? "blips" : "blip";
            return new Uri($"{scheme}://{baseUrl.Host}:{publicPort}");
        }

        #endregion

        #region Public Methods

        public SyncGateway AsSyncGateway() => _syncGateway;

        [NotNull]
        public Uri GetReplicationUrl(string dbName) => new Uri(_replicationUrl, dbName);

        #endregion

        #region Private Methods

        private string FindKeyValue(string rawJson, string key)
        {
            if (rawJson == null) {
                return null;
            }

            var regex = new Regex($"\"{key}\"\\s*:\\s*\"([^\"]+)\"");
            return regex.Matches(rawJson).FirstOrDefault()?.Groups[1]?.Value;
        }

        private int ParsePort(string value, int defaultVal)
        {
            if (value == null) {
                return defaultVal;
            }

            var raw = value.Split(':')?.Last();
            if (raw == null) {
                return -1;
            }

            if (!Int32.TryParse(raw, NumberStyles.AllowLeadingWhite | NumberStyles.AllowTrailingWhite,
                CultureInfo.InvariantCulture, out int port)) {
                return -1;
            }

            return port;
        }

        #endregion

        #region Overrides

        protected override IObjectRESTApi GetApi() => null;

        protected override void ReleaseUnmanagedResources()
        {
            OrchestrationApi.KillSyncGatewayAsync(this);
        }

        #endregion
    }
}