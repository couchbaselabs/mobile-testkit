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
using System.Linq;
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
                ["array_getDictionary"] = ArrayMethods.ArrayAddArray,
                ["array_addDictionary"] = ArrayMethods.ArrayAddDictionary,
                ["array_addString"] = ArrayMethods.ArrayAddString,
                ["array_create"] = ArrayMethods.ArrayCreate,
                ["array_getArray"] = ArrayMethods.ArrayGetArray,
                ["array_getDictionary"] = ArrayMethods.ArrayGetDictionary,
                ["array_getString"] = ArrayMethods.ArrayGetString,
                ["array_setDictionary"] = ArrayMethods.ArraySetArray,
                ["array_setDictionary"] = ArrayMethods.ArraySetDictionary,
                ["array_setString"] = ArrayMethods.ArraySetString,
                ["basicAuthenticator_create"] = BasicAuthenticationMethods.Create,
                ["sessionAuthenticator_create"] = SessionAuthenticationMethods.Create,
                ["databaseConfiguration_configure"] = DatabaseConfigurationMethods.Configure,
                ["databaseConfiguration_setEncryptionKey"] = DatabaseConfigurationMethods.SetEncryptionKey,
                ["database_create"] = DatabaseMethods.DatabaseCreate,
                ["database_compact"] = DatabaseMethods.DatabaseCompact,
                ["database_close"] = DatabaseMethods.DatabaseClose,
                ["database_getPath"] = DatabaseMethods.DatabasePath,
                ["database_deleteDB"] = DatabaseMethods.DatabaseDeleteDB,
                ["database_delete"] = DatabaseMethods.DatabaseDelete,
                ["database_deleteBulkDocs"] = DatabaseMethods.DatabaseDeleteBulkDocs,
                ["database_getName"] = DatabaseMethods.DatabaseGetName,
                ["database_getDocument"] = DatabaseMethods.DatabaseGetDocument,
                ["database_saveDocuments"] = DatabaseMethods.DatabaseSaveDocuments,
                ["database_purge"] = DatabaseMethods.DatabasePurge,
                ["database_save"] = DatabaseMethods.DatabaseSave,
                ["database_saveWithConcurrency"] = DatabaseMethods.DatabaseSaveWithConcurrency,
                ["database_deleteWithConcurrency"] = DatabaseMethods.DatabaseDeleteWithConcurrency,
                ["database_getCount"] = DatabaseMethods.DatabaseGetCount,
                ["databaseChangeListener_changesCount"] = DatabaseMethods.DatabaseChangeListenerChangesCount,
                ["databaseChangeListener_getChange"] = DatabaseMethods.DatabaseChangeListenerGetChange,
                ["databaseChange_getDocumentId"] = DatabaseMethods.DatabaseChangeGetDocumentId,
                ["database_addDocuments"] = DatabaseMethods.DatabaseAddDocuments,
                ["database_getDocIds"] = DatabaseMethods.DatabaseGetDocIds,
                ["database_getDocuments"] = DatabaseMethods.DatabaseGetDocuments,
                ["database_updateDocument"] = DatabaseMethods.DatabaseUpdateDocument,
                ["database_updateDocuments"] = DatabaseMethods.DatabaseUpdateDocuments,
                ["database_exists"] = DatabaseMethods.DatabaseExists,
                ["database_changeEncryptionKey"] = DatabaseMethods.DatabaseChangeEncryptionKey,
                ["database_copy"] = DatabaseMethods.DatabaseCopy, 
                ["database_getPreBuiltDb"] = DatabaseMethods.DatabaseGetPreBuiltDb,
                ["dictionary_contains"] = DictionaryMethods.DictionaryContains,
                ["dictionary_count"] = DictionaryMethods.DictionaryCount,
                ["dictionary_create"] = DictionaryMethods.DictionaryCreate,
                ["dictionary_getArray"] = DictionaryMethods.DictionaryGetArray,
                ["dictionary_getBlob"] = DictionaryMethods.DictionaryGetBlob,
                ["dictionary_getBoolean"] = DictionaryMethods.DictionaryGetBoolean,
                ["dictionary_getDate"] = DictionaryMethods.DictionaryGetDate,
                ["dictionary_getDictionary"] = DictionaryMethods.DictionaryGetDictionary,
                ["dictionary_getDouble"] = DictionaryMethods.DictionaryGetDouble,
                ["dictionary_getFloat"] = DictionaryMethods.DictionaryGetFloat,
                ["dictionary_getInt"] = DictionaryMethods.DictionaryGetInt,
                ["dictionary_getKeys"] = DictionaryMethods.DictionaryGetKeys,
                ["dictionary_getLong"] = DictionaryMethods.DictionaryGetLong,
                ["dictionary_getString"] = DictionaryMethods.DictionaryGetString,
                ["dictionary_remove"] = DictionaryMethods.DictionaryRemove,
                ["dictionary_setArray"] = DictionaryMethods.DictionarySetArray,
                ["dictionary_setBlob"] = DictionaryMethods.DictionarySetBlob,
                ["dictionary_setBoolean"] = DictionaryMethods.DictionarySetBoolean,
                ["dictionary_setDate"] = DictionaryMethods.DictionarySetDate,
                ["dictionary_setDictionary"] = DictionaryMethods.DictionarySetDictionary,
                ["dictionary_setDouble"] = DictionaryMethods.DictionarySetDouble,
                ["dictionary_setFloat"] = DictionaryMethods.DictionarySetFloat,
                ["dictionary_setInt"] = DictionaryMethods.DictionarySetInt,
                ["dictionary_setLong"] = DictionaryMethods.DictionarySetLong,
                ["dictionary_getValue"] = DictionaryMethods.DictionaryGetValue,
                ["dictionary_setString"] = DictionaryMethods.DictionarySetString,
                ["dictionary_setValue"] = DictionaryMethods.DictionarySetValue,
                ["dictionary_toMap"] = DictionaryMethods.DictionaryToMap,
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
                ["document_removeKey"] = DocumentMethods.DocumentRemoveKey,
                ["document_contains"] = DocumentMethods.DocumentContains,
                ["document_getValue"] = DocumentMethods.DocumentGetValue,
                ["document_setValue"] = DocumentMethods.DocumentSetValue,
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
                ["replicator_addReplicatorEventChangeListener"] = ReplicationMethods.AddDocumentReplicationChangeListener,
                ["replicator_removeReplicatorEventListener"] = ReplicationMethods.RemoveReplicatorEventListener,
                ["replicator_removeChangeListener"] = ReplicationMethods.RemoveChangeListener,
                ["replicator_replicatorEventGetChanges"] = ReplicationMethods.ReplicatorEventGetChanges,
                ["replicator_replicatorEventChangesCount"] = ReplicationMethods.ReplicatorEventChangesCount,
                ["replicatorConfiguration_setAuthenticator"] = ReplicatorConfigurationMethods.SetAuthenticator,
                ["replicatorConfiguration_setReplicatorType"] = ReplicatorConfigurationMethods.SetReplicatorType,
                ["replicator_changeListenerChangesCount"] = ReplicationMethods.ChangeListenerChangesCount,
                ["replicator_changeListenerGetChanges"] = ReplicationMethods.ChangeListenerChanges,
                ["replicator_resetCheckpoint"] = ReplicationMethods.ResetCheckpoint,
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
                ["query_leftJoin"] = QueryMethods.QueryLeftJoin,
                ["query_leftOuterJoin"] = QueryMethods.QueryLeftOuterJoin,
                ["query_innerJoin"] = QueryMethods.QueryInnerJoin,
                ["query_crossJoin"] = QueryMethods.QueryCrossJoin,
                ["query_greaterThan"] = QueryMethods.QueryGreaterThan,
                ["query_greaterThanOrEqualTo"] = QueryMethods.QueryGreaterThanOrEqualTo,
                ["query_lessThan"] = QueryMethods.QueryLessThan,
                ["query_lessThanOrEqualTo"] = QueryMethods.QueryLessThanOrEqualTo,
                ["query_not"] = QueryMethods.QueryNot,
                ["query_multipleSelectsDoubleValue"] = QueryMethods.MultipleSelectsDoubleValue,
                ["query_multipleSelectsOrderByLocaleValue"] = QueryMethods.MultipleSelectsOrderByLocaleValue,
                ["query_query_arthimetic"] = QueryMethods.QueryArthimetic,
                ["datatype_setLong"] = DataTypeMethods.DataTypeSetLong,
                ["datatype_setDouble"] = DataTypeMethods.DataTypeSetDouble,
                ["datatype_setFloat"] = DataTypeMethods.DataTypeSetFloat,
                ["datatype_compare"] = DataTypeMethods.DataTypeCompare,
                ["datatype_compareLong"] = DataTypeMethods.DataTypeCompareLong,
                ["datatype_compareDouble"] = DataTypeMethods.DataTypeCompareDouble,
                ["datatype_setDate"] = DataTypeMethods.DataTypeSetDate,
                ["datatype_compareDate"] = DataTypeMethods.DataTypeCompareDate,
                ["peerToPeer_serverStart"] = P2PMethods.Start_Server,
                ["peerToPeer_serverStop"] = P2PMethods.Stop_Server,
                ["peerToPeer_clientStart"] = P2PMethods.Start_Client,
                ["peerToPeer_configure"] = P2PMethods.Configure,
                ["peerToPeer_addReplicatorEventChangeListener"] = ReplicationMethods.AddReplicatorEventChangeListener,
                ["peerToPeer_removeReplicatorEventListener"] = ReplicationMethods.RemoveReplicatorEventListener,
                ["peerToPeer_replicatorEventGetChanges"] = ReplicationMethods.ReplicatorEventGetChanges,
                ["peerToPeer_replicatorEventChangesCount"] = ReplicationMethods.ReplicatorEventChangesCount,
                ["predictiveQuery_registerModel"] = PredictiveQueriesMethods.RegisterModel,
                ["predictiveQuery_unRegisterModel"] = PredictiveQueriesMethods.UnRegisterModel,
                ["predictiveQuery_getPredictionQueryResult"] = PredictiveQueriesMethods.GetPredictionQueryResult,
                ["predictiveQuery_nonDictionary"] = PredictiveQueriesMethods.NonDictionary,
                ["predictiveQuery_getEuclideanDistance"] = PredictiveQueriesMethods.GetEuclideanDistance,
                ["predictiveQuery_getSquaredEuclideanDistance"] = PredictiveQueriesMethods.GetSquaredEuclideanDistance,
                ["predictiveQuery_getCosineDistance"] = PredictiveQueriesMethods.GetCosineDistance,
                ["predictiveQuery_getNumberOfCalls"] = PredictiveQueriesMethods.GetNumberOfCalls,
                ["logging_configure"] = FileLoggingMehtod.Configure,
                ["logging_getPlainTextStatus"] = FileLoggingMehtod.GetPlainTextStatus,
                ["logging_getMaxRotateCount"] = FileLoggingMehtod.GetMaxRotateCount,
                ["logging_getMaxSize"] = FileLoggingMehtod.GetMaxSize,
                ["logging_getLogLevel"] = FileLoggingMehtod.GetLogLevel,
                ["logging_getConfig"] = FileLoggingMehtod.GetConfig,
                ["logging_getDirectory"] = FileLoggingMehtod.GetDirectory,
                ["logging_setPlainTextStatus"] = FileLoggingMehtod.SetPlainTextStatus,
                ["logging_setMaxRotateCount"] = FileLoggingMehtod.SetMaxRotateCount,
                ["logging_setMaxSize"] = FileLoggingMehtod.SetMaxSize,
                ["logging_setLogLevel"] = FileLoggingMehtod.SetLogLevel,
                ["logging_setConfig"] = FileLoggingMehtod.SetConfig,
                ["copy_files"] = CopyFiles,
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

        private static void CopyFiles([NotNull]NameValueCollection args,
            [NotNull]IReadOnlyDictionary<string, object> postBody,
            [NotNull]HttpListenerResponse response)
        {
            string sourcePath = postBody["source_path"].ToString();
            string destinationPath = postBody["destination_path"].ToString();
            DirectoryCopy(sourcePath, destinationPath, true);
            response.WriteBody("Copied");

        }

        private static void DirectoryCopy(string sourceDirName, string destDirName, bool copySubDirs)
        {
            // Get the subdirectories for the specified directory.
            DirectoryInfo dir = new DirectoryInfo(sourceDirName);
            Console.WriteLine("Copying " + sourceDirName + " to " + destDirName);
            if (!dir.Exists)
            {
                throw new DirectoryNotFoundException(
                    "Source directory does not exist or could not be found: "
                    + sourceDirName);
            }

            DirectoryInfo[] dirs = dir.GetDirectories();
            // If the destination directory doesn't exist, create it.
            if (!Directory.Exists(destDirName))
            {
                Directory.CreateDirectory(destDirName);
            }

            // Get the files in the directory and copy them to the new location.
            FileInfo[] files = dir.GetFiles();
            foreach (FileInfo file in files)
            {
                string temppath = Path.Combine(destDirName, file.Name);
                file.CopyTo(temppath, false);
            }

            // If copying subdirectories, copy them and their contents to new location.
            if (copySubDirs)
            {
                foreach (DirectoryInfo subdir in dirs)
                {
                    string temppath = Path.Combine(destDirName, subdir.Name);
                    DirectoryCopy(subdir.FullName, temppath, copySubDirs);
                }
            }
        }

        #endregion
    }
}