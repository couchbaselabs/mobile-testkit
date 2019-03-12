// 
//  DatabaseMethods.cs
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
using System.Linq;
using System.Net;
using System.Threading.Tasks;
using static Couchbase.Lite.DatabaseChangedEventArgs;

using Couchbase.Lite.Query;
using static Couchbase.Lite.Query.QueryBuilder;
using static Couchbase.Lite.EncryptionKey;


using JetBrains.Annotations;

using Newtonsoft.Json.Linq;
using System.IO;

namespace Couchbase.Lite.Testing
{
    public static class DatabaseMethods
    {
        #region Public Methods

        public static void With<T>([NotNull]IReadOnlyDictionary<string, object> postBody, string key, [NotNull]Action<T> action)
        {

            var handle = postBody[key].ToString();
            var db = MemoryMap.Get<T>(handle);
            action(db);
        }

        public static async Task AsyncWith<T>([NotNull]IReadOnlyDictionary<string, object> postBody, string key, [NotNull]Func<T, Task> action)
        {
            var handle = postBody[key].ToString();
            var db = MemoryMap.Get<T>(handle);
            await action(db);
        }

        #endregion

        #region Internal Methods

        // TODO. Have to write this function
        //internal static void DatabaseAddChangeListener([NotNull] NameValueCollection args,
        //    [NotNull] IReadOnlyDictionary<string, object> postBody,
        //    [NotNull] HttpListenerResponse response)
        //{
        //    With<Database>(postBody, "database", db =>
        //    {
        //        var listener = new DatabaseChangeListenerProxy();
        //        db.Changed += listener.HandleChange;
        //        var listenerId = MemoryMap.Store(listener);
        //        response.WriteBody(listenerId);
        //    });
        //}

        internal static void DatabaseAddDocuments([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                foreach (var pair in postBody)
                {
                    var val = (pair.Value as JObject)?.ToObject<IDictionary<string, object>>();
                    using (var doc = new MutableDocument(pair.Key, val))
                    {
                        db.Save(doc);
                    }
                }

                response.WriteEmptyBody();
            });
        }

        internal static void DatabaseChangeGetDocumentId([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<DatabaseChangedEventArgs>(postBody, "change", dc => response.WriteBody(dc.DocumentIDs));
        }

        internal static void DatabaseChangeListenerChangesCount([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<DatabaseChangeListenerProxy>(postBody, "changeListener", l => response.WriteBody(l.Changes.Count));
        }

        internal static void DatabaseChangeListenerGetChange([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var index = args.GetLong("index");
            With<DatabaseChangeListenerProxy>(postBody, "changeListener", l =>
            {
                var retVal = MemoryMap.Store(l.Changes[(int)index]);
                response.WriteBody(retVal);
            });
        }

        internal static void DatabaseClose([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => db.Close());
            response.WriteEmptyBody();
        }

        internal static void DatabaseCompact([NotNull] NameValueCollection args,
                                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                                             [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => db.Compact());
            response.WriteEmptyBody();
        }

        internal static void DatabaseChangeEncryptionKey([NotNull] NameValueCollection args,
                                             [NotNull] IReadOnlyDictionary<string, object> postBody,
                                             [NotNull] HttpListenerResponse response)
        {

            With<Database>(postBody, "database", db =>
            {
                var password = postBody["password"].ToString();
                if (password == "nil")
                    db.ChangeEncryptionKey(null);
                else
                {
                    var encryptionKey = new EncryptionKey(password); ;
                    db.ChangeEncryptionKey(encryptionKey);
                }
            });
            response.WriteEmptyBody();
        }

        internal static void DatabaseCreate([NotNull]NameValueCollection args,
            [NotNull]IReadOnlyDictionary<string, object> postBody,
            [NotNull]HttpListenerResponse response)
        {
            var name = postBody["name"];
            if (postBody.ContainsKey("config"))
            {
                With<DatabaseConfiguration>(postBody, "config", config => response.WriteBody(MemoryMap.New<Database>(name, config)));
            }
            else
            {
                var databaseId = MemoryMap.New<Database>(name, default(DatabaseConfiguration));
                response.WriteBody(databaseId);
            }
        }

        internal static void DatabaseDeleteDB([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => db.Delete());
            response.WriteEmptyBody();
        }

        internal static void DatabaseDelete([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
                           With<Document>(postBody, "document", doc => db.Delete(doc)));
            response.WriteEmptyBody();
        }

        internal static void DatabaseDeleteBulkDocs([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var docIds = ((List<object>)postBody["doc_ids"]).OfType<string>();
            With<Database>(postBody, "database", db =>
            {
                db.InBatch(() =>
                {
                    foreach (var docId in docIds)
                    {
                        Document doc = db.GetDocument(docId);
                        db.Delete(doc);
                    }
                });
            });
            response.WriteEmptyBody();
        }

        internal static void DatabaseDeleteByName([NotNull] NameValueCollection args,
                                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                  [NotNull] HttpListenerResponse response)
        {
            string dbName = postBody["name"].ToString();
            string directory = postBody["name"].ToString();

            Database.Delete(dbName, directory);
            response.WriteEmptyBody();
        }

        internal static void DatabaseExists([NotNull] NameValueCollection args,
                                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                  [NotNull] HttpListenerResponse response)
        {
            var name = postBody["name"].ToString();
            var directory = postBody["directory"].ToString();
            response.WriteBody(Database.Exists(name, directory));
        }

        internal static void DatabaseGetCount([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => response.WriteBody(db.Count));
        }

        internal static void DatabaseGetDocIds([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            IExpression limit = Expression.Int((int)postBody["limit"]);
            IExpression offset = Expression.Int((int)postBody["offset"]);
            With<Database>(postBody, "database", db =>
            {
                using (IQuery query = Query.QueryBuilder
                       .Select(SelectResult.Expression(Meta.ID))
                       .From(DataSource.Database(db))
                       .Limit(limit, offset))
                {
                    var result = query.Execute();
                    var ids = result.Select(x => x.GetString("id")).ToList();
                    response.WriteBody(ids);
                }
            });
        }

        internal static void DatabaseGetDocument([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            string docId = null;
            if (postBody.ContainsKey("id"))
            {
                docId = postBody["id"].ToString();
            }

            With<Database>(postBody, "database", db =>
            {
                var doc = db.GetDocument(docId);
                if (doc != null)
                {
                    response.WriteBody(MemoryMap.Store(doc));
                }
                else
                {
                    response.WriteEmptyBody();
                }

            });
        }

        internal static void DatabaseGetDocuments([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            var ids = ((List<object>)postBody["ids"]).OfType<string>();
            With<Database>(postBody, "database", db =>
            {
                var retVal = new Dictionary<string, object>();
                using (var query = Query.QueryBuilder
                       .Select(SelectResult.Expression(Meta.ID))
                    .From(DataSource.Database(db)))
                {
                    var result = query.Execute();
                    foreach (var id in ids)
                    {
                        using (var doc = db.GetDocument(id))
                        {
                            retVal[id] = doc.ToDictionary();
                        }
                    }

                    response.WriteBody(retVal);
                }
            });
        }

        internal static void DatabaseIndexes([NotNull] NameValueCollection args,
                                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                  [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => response.WriteBody(db.GetIndexes()));
        }

        internal static void DatabaseGetName([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => response.WriteBody(db.Name ?? String.Empty));
        }

        internal static void DatabasePath([NotNull] NameValueCollection args,
                                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                                          [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db => response.WriteBody(db.Path ?? String.Empty));
        }


        internal static void DatabasePurge([NotNull] NameValueCollection args,
                                          [NotNull] IReadOnlyDictionary<string, object> postBody,
                                          [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<MutableDocument>(postBody, "document", docid => db.Purge(docid));
                response.WriteEmptyBody();
            });
        }

        internal static void DatabaseSaveWithConcurrency([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<MutableDocument>(postBody, "document", document =>
                {
                    var concurrencyControlType = postBody["concurrencyControlType"].ToString();
                    var concurrencyType = ConcurrencyControl.LastWriteWins;

                    if (concurrencyControlType != null)
                    {
                        if (concurrencyControlType == "failOnConflict")
                        {
                            concurrencyType = ConcurrencyControl.FailOnConflict;
                        }
                        else
                        {
                            concurrencyType = ConcurrencyControl.LastWriteWins;
                        }
                    }

                    try
                    {
                        db.Save(document, concurrencyType);
                        response.WriteEmptyBody();
                    }
                    catch (InvalidOperationException e)
                    {
                        Console.WriteLine("Error saving document to DB" + e.Message);
                        response.WriteBody(e.Message);
                    }
                });
            });
        }

        internal static void DatabaseDeleteWithConcurrency([NotNull] NameValueCollection args,
                                         [NotNull] IReadOnlyDictionary<string, object> postBody,
                                         [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<Document>(postBody, "document", document =>
                {
                    var concurrencyControlType = postBody["concurrencyControlType"].ToString();
                    var concurrencyType = ConcurrencyControl.LastWriteWins;

                    if (concurrencyControlType != null)
                    {
                        if (concurrencyControlType == "failOnConflict")
                        {
                            concurrencyType = ConcurrencyControl.FailOnConflict;
                        }
                        else
                        {
                            concurrencyType = ConcurrencyControl.LastWriteWins;
                        }
                    }

                    try
                    {
                        db.Delete(document, concurrencyType);
                        response.WriteEmptyBody();
                    }
                    catch (InvalidOperationException e)
                    {
                        Console.WriteLine("Error deleting DB" + e.Message);
                        response.WriteBody(e.Message);
                    }
                });
            });
        }

        // TODO: Have to write complete function
        //internal static void DatabaseRemoveChangeListener([NotNull] NameValueCollection args,
        //    [NotNull] IReadOnlyDictionary<string, object> postBody,
        //    [NotNull] HttpListenerResponse response)
        //{
        //    With<Database>(postBody, "database", db => With<DatabaseChangeListenerProxy>(postBody, "changeListener", l =>
        //    {
        //        db.Changed -= l.HandleChange;
        //    }));

        //    response.WriteEmptyBody();
        //}

        internal static void DatabaseSave([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<MutableDocument>(postBody, "document", doc =>
                {
                    db.Save(doc);
                    response.WriteEmptyBody();
                });
            });
        }

        internal static void DatabaseSaveDocuments([NotNull] NameValueCollection args,
                                                   [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                   [NotNull] HttpListenerResponse response)
        {
            var docDict = (Dictionary<string, object>)postBody["documents"];
            With<Database>(postBody, "database", db =>
            {
                db.InBatch(() =>
               {
                   foreach (var body in docDict)
                   {
                       string id = body.Key;
                       var docBody = (Dictionary<string, object>)body.Value;
                       docBody.Remove("_id");
                       MutableDocument doc = new MutableDocument(id, docBody);
                       db.Save(doc);

                   }
               });
            });
            response.WriteEmptyBody();
        }


        internal static void DatabaseUpdateDocument([NotNull] NameValueCollection args,
                                           [NotNull] IReadOnlyDictionary<string, object> postBody,
                                           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                string id = postBody["id"].ToString();
                Dictionary<string, Object> data = (Dictionary<string, Object>)postBody["data"];
                MutableDocument UpdateDoc = db.GetDocument(id).ToMutable();
                UpdateDoc.SetData(data);
                db.Save(UpdateDoc);
                response.WriteEmptyBody();
            });
            response.WriteEmptyBody();
        }
        internal static void DatabaseUpdateDocuments([NotNull] NameValueCollection args,
                                   [NotNull] IReadOnlyDictionary<string, object> postBody,
                                   [NotNull] HttpListenerResponse response)
        {
            var docDict = (Dictionary<string, object>)postBody["documents"];
            With<Database>(postBody, "database", db =>
            {
                db.InBatch(() =>
                {
                    foreach (var body in docDict)
                    {
                        string id = body.Key;
                        Dictionary<string, Object> docVal = (Dictionary<string, object>)body.Value;
                        MutableDocument UpdateDoc = db.GetDocument(id).ToMutable();
                        UpdateDoc.SetData(docVal);
                        db.Save(UpdateDoc);
                    }
                });
            });
            response.WriteEmptyBody();
        }
        internal static void DatabaseCopy([NotNull] NameValueCollection args,
                                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                                  [NotNull] HttpListenerResponse response)
        {
            string dbName = postBody["dbName"].ToString();
            string dbPath = TestServer.FilePathResolver(postBody["dbPath"].ToString());
            dbPath = dbPath + "/";
            DatabaseConfiguration dbConfig = MemoryMap.Get<DatabaseConfiguration>(postBody["dbConfig"].ToString());
            Database.Copy(dbPath, dbName, dbConfig);
            response.WriteEmptyBody();
        }


#endregion
    }

    internal sealed class DatabaseChangeListenerProxy
    {
#region Variables

        [NotNull]
        private readonly List<DatabaseChangedEventArgs> _changes = new List<DatabaseChangedEventArgs>();

#endregion

#region Properties

        [NotNull]
        public IReadOnlyList<DatabaseChangedEventArgs> Changes => _changes;

#endregion

#region Public Methods

        public void HandleChange(object sender, DatabaseChangedEventArgs args)
        {
            _changes.Add(args);
        }

#endregion
    }

}