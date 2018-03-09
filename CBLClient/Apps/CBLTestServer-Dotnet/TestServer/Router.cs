// 
//  Router.cs
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
using System.Collections.Specialized;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;

using JetBrains.Annotations;

using Newtonsoft.Json;

using HandlerAction = System.Action<System.Collections.Specialized.NameValueCollection,
    System.Collections.Generic.IReadOnlyDictionary<string, object>,
    System.Net.HttpListenerResponse>;

namespace Couchbase.Lite.Testing
{
    public static class Router
    {
        #region Constants

        [NotNull]
        private static readonly IDictionary<string, HandlerAction> RouteMap =
            new Dictionary<string, HandlerAction>
            {
            ["basicAuthenticator_create"] = BasicAuthenticationMethods.Create,
            ["sessionAuthenticator_create"] = SessionAuthenticationMethods.Create,
            ["databaseConfiguration_configure"] = DatabaseConfigurationMethods.Configure,
            ["database_deleteBulkDocs"] = DatabaseMethods.DatabaseDeleteBulkDocs,
            ["database_create"] = DatabaseMethods.DatabaseCreate,
            ["database_close"] = DatabaseMethods.DatabaseClose,
            ["database_getPath"] = DatabaseMethods.DatabasePath,
            ["database_deleteDB"] = DatabaseMethods.DatabaseDeleteDB,
            ["database_delete"] = DatabaseMethods.DatabaseDelete,
            ["database_getName"] = DatabaseMethods.DatabaseGetName,
            ["database_getDocument"] = DatabaseMethods.DatabaseGetDocument,
            ["database_saveDocuments"] = DatabaseMethods.DatabaseSaveDocuments,
            ["database_purge"] = DatabaseMethods.DatabasePurge,
            ["database_save"] = DatabaseMethods.DatabaseSave,
            ["database_getCount"] = DatabaseMethods.DatabaseGetCount,
            ["databaseChangeListener_changesCount"] = DatabaseMethods.DatabaseChangeListenerChangesCount,
            ["databaseChangeListener_getChange"] = DatabaseMethods.DatabaseChangeListenerGetChange,
            ["databaseChange_getDocumentId"] = DatabaseMethods.DatabaseChangeGetDocumentId,
            ["database_addDocuments"] = DatabaseMethods.DatabaseAddDocuments,
            ["database_getDocIds"] = DatabaseMethods.DatabaseGetDocIds,
            ["database_getDocuments"] = DatabaseMethods.DatabaseGetDocuments,
            ["database_updateDocument"] = DatabaseMethods.DatabaseUpdateDocument,
            ["database_updateDocuments"] = DatabaseMethods.DatabaseUpdateDocuments,
            ["document_create"] = DocumentMethods.DocumentCreate,
            ["document_delete"] = DocumentMethods.DocumentDelete,
            ["document_getId"] = DocumentMethods.DocumentGetId,
            ["document_getString"] = DocumentMethods.DocumentGetString,
            ["document_setString"] = DocumentMethods.DocumentSetString,
            ["document_count"] = DocumentMethods.DocumentCount,
            ["document_getInt"] = DocumentMethods.DocumentGetInt,
            ["document_setInt"] = DocumentMethods.DocumentSetInt,
            ["document_getLong"] = DocumentMethods.DocumentGetLong,
            ["document_setLong"] = DocumentMethods.DocumentSetLong,
            ["document_getFloat"] = DocumentMethods.DocumentGetFloat,
            ["document_setFloat"] = DocumentMethods.DocumentSetFloat,
            ["document_getDouble"] = DocumentMethods.DocumentGetDouble,
            ["document_setDouble"] = DocumentMethods.DocumentSetDouble,
            ["document_getBoolean"] = DocumentMethods.DocumentGetBoolean,
            ["document_setBoolean"] = DocumentMethods.DocumentSetBoolean,
            ["document_getBlob"] = DocumentMethods.DocumentGetBlob,
            ["document_setBlob"] = DocumentMethods.DocumentSetBlob,
            ["document_getArray"] = DocumentMethods.DocumentGetArray,
            ["document_setArray"] = DocumentMethods.DocumentSetArray,
            ["document_getDate"] = DocumentMethods.DocumentGetDate,
            ["document_setDate"] = DocumentMethods.DocumentSetDate,
            ["document_setData"] = DocumentMethods.DocumentSetData,
            ["document_getDictionary"] = DocumentMethods.DocumentGetDictionary,
            ["document_setDictionary"] = DocumentMethods.DocumentSetDictionary,
            ["document_getKeys"] = DocumentMethods.DocumentGetKeys,
            ["document_toMap"] = DocumentMethods.DocumentToDictionary,
            ["document_toMutable"] = DocumentMethods.DocumentToMutable,
            ["document_remove"] = DocumentMethods.DocumentRemoveKey,
            ["document_contains"] = DocumentMethods.DocumentContains,
            ["replicatorConfiguration_configure"] = ReplicatorConfigurationMethods.Configure,
            ["replicator_create"] = ReplicationMethods.Create,
            ["replicator_start"] = ReplicationMethods.StartReplication,
            ["replicator_stop"] = ReplicationMethods.StopReplication,
            ["replicator_status"] = ReplicationMethods.Status,
            ["replicator_getActivityLevel"] = ReplicationMethods.GetActivityLevel,
            ["replicator_getError"] = ReplicationMethods.GetError,
            ["replicator_getTotal"] = ReplicationMethods.GetTotal,
            ["replicator_getConfig"] = ReplicationMethods.GetConfig,
            ["replicator_getCompleted"] = ReplicationMethods.GetCompleted,
            ["replicator_addChangeListener"] = ReplicationMethods.AddChangeListener,
            ["replicator_removeChangeListener"] = ReplicationMethods.RemoveChangeListener,
            ["replicatorConfiguration_setAuthenticator"] = ReplicatorConfigurationMethods.SetAuthenticator,
            ["replicator_changeListenerChangesCount"] = ReplicationMethods.ChangeListenerChangesCount,
            ["replicator_changeListenerGetChanges"] = ReplicationMethods.ChangeListenerChanges,
            ["configure_replication"] = ReplicatorConfigurationMethods.Configure,
            ["replication_getStatus"] = ReplicationMethods.Status,
            ["collator_ascii"] = CollatorMethods.Ascii,
            ["collator_unicode"] = CollatorMethods.Unicode,
            ["expression_property"] = ExpressionMethods.ExpressionProperty,
            ["expression_sequence"] = ExpressionMethods.ExpressionSequence,
            ["expression_parameter"] = ExpressionMethods.ExpressionParameter,
            ["expression_negated"] = ExpressionMethods.ExpressionNegated,
            ["expression_not"] = ExpressionMethods.ExpressionNot,
            ["expression_variable"] = ExpressionMethods.ExpressionVariable,
            ["expression_any"] = ExpressionMethods.ExpressionAny,
            ["expression_anyAndEvery"] = ExpressionMethods.ExpressionAnyAndEvery,
            ["expression_every"] = ExpressionMethods.ExpressionEvery,
            ["expression_createEqualTo"] = ExpressionMethods.ExpressionCreateEqualTo,
            ["expression_createAnd"] = ExpressionMethods.ExpressionCreateAnd,
            ["expression_createOr"] = ExpressionMethods.ExpressionCreateOr,
            ["datasource_database"] = DataSourceMethods.Database,
            ["query_create"] = QueryMethods.QueryCreate,
            ["query_getDoc"] = QueryMethods.QueryGetDoc,
            ["query_like"] = QueryMethods.QueryLike,
            ["query_run"] = QueryMethods.QueryRun,
            ["query_nextResult"] = QueryMethods.QueryNextResult,
            ["query_docsLimitOffset"] = QueryMethods.QueryDocsLimitOffset,
            ["query_multipleSelects"] = QueryMethods.QueryMultipleSelects,
            ["query_whereAndOr"] = QueryMethods.QueryWhereAndOr,
            ["query_regex"] = QueryMethods.QueryRegex,
            ["query_isNullOrMissing"] = QueryMethods.QueryIsNullOrMissing,
            ["query_ordering"] = QueryMethods.QueryOrdering,
            ["query_substring"] = QueryMethods.QuerySubstring,
            ["query_collation"] = QueryMethods.Querycollation,
            ["query_multiplePropertyFTS"] = QueryMethods.QueryMultiplePropertyFTS,
            ["query_singlePropertyFTS"] = QueryMethods.QuerySinglePropertyFTS,
            ["query_ftsWithRanking"] = QueryMethods.QueryFTSWithRanking,
            ["query_equalTo"] = QueryMethods.QueryEqualTo,
            ["query_notEqualTo"] = QueryMethods.QueryNotEqualTo,
            ["query_between"] = QueryMethods.QueryBetween,
            ["query_in"] = QueryMethods.QueryIn,
            ["query_is"] = QueryMethods.QueryIs,
            ["query_isNot"] = QueryMethods.QueryIsNot,
            ["query_join"] = QueryMethods.QueryJoin,
            ["query_join2"] = QueryMethods.QueryJoin2,
            ["query_greaterThan"] = QueryMethods.QueryGreaterThan,
            ["query_greaterThanOrEqualTo"] = QueryMethods.QueryGreaterThanOrEqualTo,
            ["query_lessThan"] = QueryMethods.QueryLessThan,
            ["query_lessThanOrEqualTo"] = QueryMethods.QueryLessThanOrEqualTo,
            ["query_not"] = QueryMethods.QueryNot,
            ["release"] = ReleaseObject,
            ["flushMemory"] = flushMemory
            };

        #endregion

        #region Public Methods

        public static void Extend([NotNull]IDictionary<string, HandlerAction> extensions)
        {
            foreach (var pair in extensions)
            {
                if (!RouteMap.ContainsKey(pair.Key))
                {
                    RouteMap[pair.Key] = pair.Value;
                }
            }
        }

        #endregion

        #region Internal Methods

        internal static void Handle([NotNull]Uri endpoint, [NotNull]Stream body, [NotNull]HttpListenerResponse response)
        {
            if (!RouteMap.TryGetValue(endpoint.AbsolutePath?.TrimStart('/'), out HandlerAction action))
            {
                response.WriteEmptyBody(HttpStatusCode.NotFound);
                return;
            }


            Dictionary<string, string> jsonObj;
            Dictionary<string, object> bodyObj;
            try
            {
                var serializer = JsonSerializer.CreateDefault();
                using (var reader = new JsonTextReader(new StreamReader(body, Encoding.UTF8, false, 8192, false)))
                {
                    reader.CloseInput = true;
                    jsonObj = serializer?.Deserialize<Dictionary<string, string>>(reader) ?? new Dictionary<string, string>();
                    bodyObj = ValueSerializer.Deserialize(jsonObj);
                }
            }
            catch (Exception e)
            {
                Debug.WriteLine($"Error deserializing POST body for {endpoint}: {e}");
                Console.WriteLine($"Error deserializing POST body for {endpoint}: {e.Message}");
                response.WriteBody("Invalid JSON body received");
                return;
            }

            var args = endpoint.ParseQueryString();
            try
            {
                action(args, bodyObj, response);
            }
            catch (Exception e)
            {
                Debug.WriteLine($"Error in handler for {endpoint}: {e}");
                Console.WriteLine($"Error in handler for {endpoint}: {e.Message}");
                response.WriteBody(e.Message?.Replace("\r", "")?.Replace('\n', ' ') ?? String.Empty, false);
            }
        }

        #endregion

        #region Private Methods

        private static void ReleaseObject([NotNull]NameValueCollection args,
            [NotNull]IReadOnlyDictionary<string, object> postBody,
            [NotNull]HttpListenerResponse response)
        {
            var id = postBody["object"].ToString();
            MemoryMap.Release(id);
        }

        private static void flushMemory([NotNull]NameValueCollection args,
            [NotNull]IReadOnlyDictionary<string, object> postBody,
            [NotNull]HttpListenerResponse response)
        {
            MemoryMap.Clear();
            response.WriteEmptyBody(HttpStatusCode.OK);
            return;
        }

        #endregion
    }
}