// 
//  IDatabaseRESTApi.cs
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
    public interface IDatabaseRESTApi : IObjectRESTApi
    {
        #region Public Methods

        [NotNull]
        [Post("database_addChangeListener")]
        Task<long> AddChangeListenerAsync(long database);

        [NotNull]
        [Post("database_addDocuments")]
        Task AddDocumentsAsync(long database, [Body]Dictionary<string, Dictionary<string, object>> body);

        [NotNull]
        [Post("database_close")]
        Task CloseAsync(long database);

        [NotNull]
        [Post("database_contains")]
        Task<bool> ContainsAsync(long database, string id);

        [NotNull]
        [Post("database_create")]
        Task<long> CreateAsync(string name);

        [NotNull]
        [Post("database_delete")]
        Task DeleteAsync(string name, string path);

        [NotNull]
        [Post("database_docCount")]
        Task<ulong> DocCountAsync(long database);

        [NotNull]
        [ItemNotNull]
        [Post("database_getDocIds")]
        Task<string[]> GetDocIdsAsync(long database);

        [NotNull]
        [Post("database_getDocument")]
        Task<long> GetDocumentAsync(long database, string id);

        [NotNull]
        [ItemNotNull]
        [Post("database_getDocuments")]
        Task<IReadOnlyDictionary<string, IReadOnlyDictionary<string, object>>> GetDocumentsAsync(long database);

        [NotNull]
        [ItemNotNull]
        [Post("database_getName")]
        Task<string> GetNameAsync(long database);

        [NotNull]
        [ItemNotNull]
        [Post("database_path")]
        Task<string> PathAsync(long database);

        [NotNull]
        [Post("database_removeChangeListener")]
        Task RemoveChangeListenerAsync(long database, long changeListener);

        [NotNull]
        [Post("database_save")]
        Task SaveAsync(long database, long document);

        #endregion
    }
}