// 
//  RemoteProxyDocument.cs
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
    public sealed class RemoteProxyDocument : RemoteProxyObject
    {
        #region Constants

        [NotNull] 
        private static readonly IDocumentRESTApi Api = RestClient.For<IDocumentRESTApi>(Program.ServerUrl)
                                                                 ?? throw new ApplicationException("Unable to create document REST API");

        #endregion

        public RemoteProxyDatabase Owner { get; set; }

        #region Constructors

        public RemoteProxyDocument([NotNull]string id, [NotNull]RemoteProxyDictionary dictionary)
            : base(Api.CreateAsync(id, dictionary).Result)
        {
        }

        public RemoteProxyDocument(long handle) : base(handle)
        {
        }

        #endregion

        [NotNull]
        public Task DeleteAsync() => Api.DeleteAsync(Owner, this);

        [NotNull]
        [ItemNotNull]
        public Task<string> GetIdAsync() => Api.GetIdAsync(this);

        [NotNull]
        public Task<string> GetStringAsync([NotNull]string key) => Api.GetStringAsync(this, key);

        [NotNull]
        public Task SetStringAsync([NotNull] string key, [NotNull] string val) => Api.SetStringAsync(this, key, val);

        #region Overrides

        protected override IObjectRESTApi GetApi() => Api;

        #endregion
    }
}