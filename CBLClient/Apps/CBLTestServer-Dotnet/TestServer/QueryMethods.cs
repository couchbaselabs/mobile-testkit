// 
//  QueryMethods.cs
// 
//  Author:
//   Hemant Rajput  <hemant.rajput@couchbase.com>
// 
//  Copyright (c) 2018 Couchbase, Inc All rights reserved.
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
using System.Net;
using System.Reflection;

using Couchbase.Lite.Query;
using Couchbase.Lite.Util;

using JetBrains.Annotations;

using static Couchbase.Lite.Testing.DatabaseMethods;

namespace Couchbase.Lite.Testing
{
    internal static class QueryMethods
    {
        internal static void QuerySelect([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ISelectResult>(postBody, "select_result", se => response.WriteBody(MemoryMap.Store(QueryBuilder.Select(se))));
        }

        internal static void QueryCreate([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ISelectResult>(postBody, "select_result", se => response.WriteBody(MemoryMap.Store(QueryBuilder.Select(se))));
        }

        internal static void QueryDistinct([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ISelectResult>(postBody, "select_result", se =>
            {
                With<IDataSource>(postBody, "from_pop", ds =>
                {
                    With<IExpression>(postBody, "whr_key_prop", exp => response.WriteBody(MemoryMap.Store(QueryBuilder.Select(se).From(ds).Where(exp))));
                });
            });
        }

        internal static void QueryRun([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<IQuery>(postBody, "query", query => response.WriteBody(MemoryMap.Store(query.Execute())));
        }

        internal static void QueryNextResult([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<ISelectResult>(postBody, "select_result", se => response.WriteBody(MemoryMap.Store(QueryBuilder.Select(se))));
        }

        internal static void QueryGetDoc([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                ulong cnt = db.Count;
                var doc_id = postBody["doc_id"].ToString();
                IExpression docId = Expression.Value(doc_id);
                IQuery query = QueryBuilder
                                .Select(SelectResult.All())
                                .From(DataSource.Database(db))
                                .Where(Meta.ID.EqualTo(docId));

                List <Dictionary<String, object>> resultArray = new List<Dictionary<String, object>>();

                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }

                response.WriteBody(resultArray);
            });
        }

        internal static void QueryDocsLimitOffset([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                IExpression limit = Expression.Value(postBody["limit"].ToString());
                IExpression offset = Expression.Value(postBody["offset"].ToString());
                IQuery query = QueryBuilder
                                .Select(SelectResult.All())
                                .From(DataSource.Database(db))
                                .Limit(limit, offset);
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryMultipleSelects([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                IExpression whrVal = Expression.Value(postBody["whr_val"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryWhereAndOr([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var whrKey1 = postBody["whr_key1"].ToString();
                var whrKey2 = postBody["whr_key2"].ToString();
                var whrKey3 = postBody["whr_key3"].ToString();
                var whrKey4 = postBody["whr_key4"].ToString();
                IExpression whrVal1 = Expression.Value(postBody["whr_val1"].ToString());
                IExpression whrVal2 = Expression.Value(postBody["whr_val2"].ToString());
                IExpression whrVal3 = Expression.Value(postBody["whr_val3"].ToString());
                IExpression whrVal4 = Expression.Value(postBody["whr_val4"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey1).EqualTo(whrVal1)
                                        .And(Expression.Property(whrKey2).EqualTo(whrVal2)
                                            .Or(Expression.Property(whrKey3).EqualTo(whrVal3)))
                                        .And(Expression.Property(whrKey4).EqualTo(whrVal4)));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryLike([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                var likeKey = postBody["like_key"].ToString();
                IExpression whrVal = Expression.Value(postBody["whr_val"].ToString());
                IExpression likeVal = Expression.Value(postBody["like_val"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)
                                        .And(Expression.Property(likeKey).Like(likeVal)));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryRegex([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                var regexKey = postBody["regex_key"].ToString();
                IExpression whrVal = Expression.Value(postBody["whr_val"].ToString());
                IExpression regexVal = Expression.Value(postBody["regex_val"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)
                                        .And(Expression.Property(regexKey).Regex(regexVal)));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryOrdering([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                IExpression whrVal = Expression.Value(postBody["whr_val"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal))
                                .OrderBy(Ordering.Property(prop1).Ascending());
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QuerySubstring([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                IExpression substring = Expression.Value(postBody["substring"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Function.Contains(Expression.Property(prop1), substring));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryIsNullOrMissing([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                IExpression limit = Expression.Value(postBody["limit"].ToString());

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(prop1).IsNullOrMissing())
                                .OrderBy(Ordering.Expression(Meta.ID).Ascending())
                                .Limit(limit);
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void Querycollation([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var whrKey1 = postBody["whr_key1"].ToString();
                var whrKey2 = postBody["whr_key2"].ToString();
                IExpression whrVal1 = Expression.Value(postBody["whr_val1"].ToString());
                IExpression whrVal2 = Expression.Value(postBody["whr_val2"].ToString());
                IExpression equal_to = Expression.Value(postBody["equal_to"].ToString());

                ICollation collation = Collation.Unicode().IgnoreAccents(true).IgnoreCase(true);
                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey1).EqualTo(whrVal1)
                                        .And(Expression.Property(whrKey2).EqualTo(whrVal2))
                                        .And((Expression.Property(prop1).Collate(collation).EqualTo(equal_to))));
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }


        internal static void QuerySinglePropertyFTS([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                var val = postBody["val"].ToString();
                Boolean stemming = Convert.ToBoolean(postBody["stemming"]);
                IExpression limit = Expression.Value(postBody["limit"].ToString());
                IExpression doc_type = Expression.Value(postBody["doc_type"].ToString());
                string index = "singlePropertyIndex";

                IFullTextIndex ftsIndex;
                if (stemming)
                {
                    ftsIndex = IndexBuilder.FullTextIndex(FullTextIndexItem.Property(prop));
                } 
                else
                {
                    ftsIndex = IndexBuilder.FullTextIndex(FullTextIndexItem.Property(prop)).SetLanguage(null);
                }
                db.CreateIndex(index, ftsIndex);
                IFullTextExpression ftsExpression = FullTextExpression.Index(index);

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .Limit(limit);
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryMultiplePropertyFTS([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["prop1"].ToString();
                var prop2 = postBody["prop2"].ToString();
                var val = postBody["val"].ToString();
                Boolean stemming = Convert.ToBoolean(postBody["stemming"]);
                IExpression limit = Expression.Value(postBody["limit"].ToString());
                IExpression doc_type = Expression.Value(postBody["doc_type"].ToString());
                string index = "singlePropertyIndex";

                IFullTextIndex ftsIndex;
                if (stemming) 
                {
                    ftsIndex = IndexBuilder.FullTextIndex(FullTextIndexItem.Property(prop1), FullTextIndexItem.Property(prop2));  
                }
                else
                {
                    ftsIndex = IndexBuilder.FullTextIndex(FullTextIndexItem.Property(prop1), FullTextIndexItem.Property(prop2)).SetLanguage(null);
                }
                db.CreateIndex(index, ftsIndex);
                IFullTextExpression ftsExpression = FullTextExpression.Index(index);

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .Limit(limit);
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryFTSWithRanking([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                var val = postBody["val"].ToString();
                IExpression limit = Expression.Value(postBody["limit"].ToString());
                IExpression doc_type = Expression.Value(postBody["doc_type"].ToString());
                string index = "singlePropertyIndex";

                IFullTextIndex ftsIndex = IndexBuilder.FullTextIndex(FullTextIndexItem.Property(prop));
                db.CreateIndex(index, ftsIndex);
                IFullTextExpression ftsExpression = FullTextExpression.Index(index);

                IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .OrderBy(Ordering.Expression(FullTextFunction.Rank(index)).Descending())
                                .Limit(limit);
                List<object> resultArray = new List<object>();
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryEqualTo([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            //SELECT * FROM `travel-sample` where id = 24
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value(postBody["val"].ToString());
                List<Object> resultArray = new List<Object>();

                IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).EqualTo(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending());
                foreach (Result row in query.Execute())
                {
                    resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });

        }

    }

}