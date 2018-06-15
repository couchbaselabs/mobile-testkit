// 
//  RemoteProxyDBChangeListener.cs
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
using System.Threading.Tasks;

using JetBrains.Annotations;

using RestEase;

namespace TestClient
{
    public sealed class RemoteProxyDBChangeListener : RemoteProxyObject
    {
        #region Constants

        [NotNull]
        private static readonly IDBChangeListenerRESTApi Api =
            RestClient.For<IDBChangeListenerRESTApi>(Program.ServerUrl)
            ?? throw new ApplicationException("Unable to create DB change listener REST API");

        #endregion

        #region Constructors

        public RemoteProxyDBChangeListener(long handle) : base(handle)
        {
        }

        #endregion

        #region Public Methods

        public async Task<RemoteProxyDBChange> GetChangeAsync(int index)
        {
            var handle = await Api.GetChangeAsync(this, index);
            return new RemoteProxyDBChange(handle);
        }

        #endregion

        #region Overrides

        protected override IObjectRESTApi GetApi() => Api;

        #endregion
    }
}