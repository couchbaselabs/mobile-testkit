// 
//  IReplicationRESTApi.cs
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

using System.Collections.Generic;
using System.Threading.Tasks;

using JetBrains.Annotations;

using RestEase;

namespace TestClient
{
    public interface IReplicationRESTApi : IObjectRESTApi
    {
        #region Public Methods

        [NotNull]
        [Post("configure_replication")]
        Task<long> ConfigureAsync(long source_db, string target_url, bool continuous = false,
            string replication_type = "pushandpull", [Body]IDictionary<string, object> authentication = null);

        [NotNull]
        [ItemNotNull]
        [Post("replication_getStatus")]
        Task<IReadOnlyDictionary<string, object>> GetStatusAsync(long replication_obj);

        [NotNull]
        [Post("start_replication")]
        Task StartAsync(long replication_obj);

        [NotNull]
        [Post("stop_replication")]
        Task StopAsync(long replication_obj);

        #endregion
    }
}