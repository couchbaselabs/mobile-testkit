// 
//  RemoteProxyDatabase.cs
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
    public sealed class RemoteProxyDatabase : RemoteProxyObject
    {
        #region Constants

        [NotNull]
        private static readonly IDatabaseRESTApi Api = RestClient.For<IDatabaseRESTApi>(Program.ServerUrl) 
                                                           ?? throw new ApplicationException("Unable to create database REST API");

        #endregion

        #region Constructors

        public RemoteProxyDatabase([NotNull]string name) : base(Api.CreateAsync(name).Result)
        {
        }

        #endregion

        #region Public Methods

        [NotNull]
        public static Task DeleteAsync([NotNull]string name, string path) => Api.DeleteAsync(name, path);

        [NotNull]
        [ItemNotNull]
        public async Task<RemoteProxyDBChangeListener> AddChangeListenerAsync()
        {
            var handle = await Api.AddChangeListenerAsync(this);
            return new RemoteProxyDBChangeListener(handle);
        }

        [NotNull]
        public Task AddDocumentsAsync(Dictionary<string, Dictionary<string, object>> docs) => Api.AddDocumentsAsync(this, docs);

        [NotNull]
        public Task CloseAsync() => Api.CloseAsync(this);

        [NotNull]
        public Task<bool> Contains([NotNull]string id) => Api.ContainsAsync(this, id);

        [NotNull]
        public Task<ulong> GetDocCountAsync() => Api.DocCountAsync(this);

        [NotNull]
        [ItemNotNull]
        public Task<string[]> GetDocIdsAsync() => Api.GetDocIdsAsync(this);

        [NotNull]
        public async Task<RemoteProxyDocument> GetDocumentAsync([NotNull]string id)
        {
            try {
                var handle = await Api.GetDocumentAsync(this, id).ConfigureAwait(false);
                return new RemoteProxyDocument(handle);
            } catch (Exception) {
                return null;
            }
        }

        [NotNull]
        [ItemNotNull]
        public Task<IReadOnlyDictionary<string, IReadOnlyDictionary<string, object>>> GetDocumentsAsync() =>
            Api.GetDocumentsAsync(this);

        [NotNull]
        [ItemNotNull]
        public Task<string> GetNameAsync() => Api.GetNameAsync(this);

        [NotNull]
        [ItemNotNull]
        public Task<string> GetPathAsync() => Api.PathAsync(this);

        [NotNull]
        public Task RemoveChangeListenerAsync([NotNull]RemoteProxyDBChangeListener listener) => Api.RemoveChangeListenerAsync(this, listener);

        [NotNull]
        public Task SaveAsync([NotNull]RemoteProxyDocument document) => Api.SaveAsync(this, document);

        #endregion

        #region Overrides

        protected override IObjectRESTApi GetApi() => Api;

        #endregion
    }
}