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
                    With<IExpression>(postBody, "whr_key_prop", exp => response.WriteBody(MemoryMap.Store(QueryBuilder.SelectDistinct(se).From(ds).Where(exp))));
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
                List<Object> resultArray = new List<Object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.All())
                                .From(DataSource.Database(db))
                                .Where(Meta.ID.EqualTo(docId)))

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
                IExpression limit = Expression.Int((int)postBody["limit"]);
                IExpression offset = Expression.Int((int)postBody["offset"]);
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.All())
                                .From(DataSource.Database(db))
                                .Limit(limit, offset))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void MultipleSelectsDoubleValue([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                var whrval = postBody["whr_val"];
                IExpression whrVal = Expression.Double((double)whrval);
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void MultipleSelectsOrderByLocaleValue([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey = postBody["whr_key"].ToString();
                var locale = postBody["locale"].ToString();
                ICollation localeCollation = Collation.Unicode().Locale(locale);
                var key = Expression.Property(whrKey);
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                       .OrderBy(Ordering.Expression(key.Collate(localeCollation))))

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
                IExpression whrVal4 = Expression.Value((Boolean)postBody["whr_val4"]);
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey1).EqualTo(whrVal1)
                                        .And(Expression.Property(whrKey2).EqualTo(whrVal2)
                                            .Or(Expression.Property(whrKey3).EqualTo(whrVal3)))
                                        .And(Expression.Property(whrKey4).EqualTo(whrVal4))))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)
                                        .And(Expression.Property(likeKey).Like(likeVal))))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal)
                                        .And(Expression.Property(regexKey).Regex(regexVal))))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey).EqualTo(whrVal))
                                .OrderBy(Ordering.Property(prop1).Ascending()))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Function.Upper(Expression.Property(prop2))))
                                .From(DataSource.Database(db))
                                .Where(Function.Contains(Expression.Property(prop1), substring)))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(prop1).IsNullOrMissing())
                                .OrderBy(Ordering.Expression(Meta.ID).Ascending())
                                .Limit(limit))

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
                List<object> resultArray = new List<object>();
                ICollation collation = Collation.Unicode().IgnoreAccents(true).IgnoreCase(true);
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property(whrKey1).EqualTo(whrVal1)
                                        .And(Expression.Property(whrKey2).EqualTo(whrVal2))
                                        .And((Expression.Property(prop1).Collate(collation).EqualTo(equal_to)))))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .Limit(limit))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop1)),
                                        SelectResult.Expression(Expression.Property(prop2)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .Limit(limit))

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
                List<object> resultArray = new List<object>();
                using (IQuery query = QueryBuilder
                                .Select(SelectResult.Expression(Meta.ID),
                                        SelectResult.Expression(Expression.Property(prop)))
                                .From(DataSource.Database(db))
                                .Where(Expression.Property("type").EqualTo(doc_type).And(ftsExpression.Match(val)))
                                .OrderBy(Ordering.Expression(FullTextFunction.Rank(index)).Descending())
                                .Limit(limit))

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
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value(postBody["val"].ToString());
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).EqualTo(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryNotEqualTo([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value(postBody["val"].ToString());
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).NotEqualTo(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryGreaterThan([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value((int)postBody["val"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).GreaterThan(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryGreaterThanOrEqualTo([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value((int)postBody["val"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).GreaterThanOrEqualTo(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryLessThan([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value((int)postBody["val"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).LessThan(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryLessThanOrEqualTo([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val = Expression.Value((int)postBody["val"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).LessThanOrEqualTo(val))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryBetween([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val1 = Expression.Value((int)postBody["val1"]);
                IExpression val2 = Expression.Value((int)postBody["val2"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).Between(val1, val2))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryIn([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val1 = Expression.Value(postBody["val1"].ToString());
                IExpression val2 = Expression.Value(postBody["val2"].ToString());
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).In(val1, val2))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryIs([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).Is(Expression.Value(null)))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryAnyOperator([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var whr_prop = postBody["whr_prop"].ToString();
                var whr_val = postBody["whr_val"].ToString();
                var schedule = postBody["schedule"].ToString();
                var departure = postBody["departure"].ToString();
                var departure_prop = postBody["departure_prop"].ToString();
                var departure_val = postBody["departure_val"].ToString();
                IVariableExpression dep_schedule = ArrayExpression.Variable(departure);
                IVariableExpression departure_utc = ArrayExpression.Variable(departure_prop);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(whr_prop).EqualTo(Expression.Value(whr_val))
                            .And(ArrayExpression.Any(dep_schedule).In(Expression.Property(schedule))
                                .Satisfies(departure_utc.GreaterThan(Expression.Value(departure_val))))))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.GetString("id"));
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryNot([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                IExpression val1 = Expression.Value((int)postBody["val1"]);
                IExpression val2 = Expression.Value((int)postBody["val2"]);
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID))
                        .From(DataSource.Database(db))
                        .Where(Expression.Not(Expression.Property(prop).Between(val1, val2)))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryIsNot([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["prop"].ToString();
                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(SelectResult.Expression(Meta.ID),
                                SelectResult.Expression(Expression.Property(prop)))
                        .From(DataSource.Database(db))
                        .Where(Expression.Property(prop).IsNot(Expression.Value(null)))
                        .OrderBy(Ordering.Expression(Meta.ID).Ascending()))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryJoin([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var prop3 = postBody["select_property3"].ToString();
                var prop4 = postBody["select_property4"].ToString();
                var prop5 = postBody["select_property5"].ToString();
                var joinKey = postBody["join_key"].ToString();
                var whrKey1 = postBody["whr_key1"].ToString();
                var whrKey2 = postBody["whr_key2"].ToString();
                var whrKey3 = postBody["whr_key3"].ToString();
                IExpression whrVal1 = Expression.Value(postBody["whr_val1"].ToString());
                IExpression whrVal2 = Expression.Value(postBody["whr_val2"].ToString());
                IExpression whrVal3 = Expression.Value(postBody["whr_val3"].ToString());
                String main = "route";
                String secondary = "airline";

                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .SelectDistinct(
                                SelectResult.Expression(Expression.Property(prop1).From(secondary)),
                                SelectResult.Expression(Expression.Property(prop2).From(secondary)),
                                SelectResult.Expression(Expression.Property(prop3).From(main)),
                                SelectResult.Expression(Expression.Property(prop4).From(main)),
                                SelectResult.Expression(Expression.Property(prop5).From(main)))
                        .From(DataSource.Database(db).As(main))
                        .Join(Join.InnerJoin(DataSource.Database(db).As(secondary))
                            .On(Meta.ID.From(secondary).EqualTo(Expression.Property(joinKey).From(main))))
                        .Where(Expression.Property(whrKey1).From(main).EqualTo(whrVal1)
                            .And(Expression.Property(whrKey2).From(secondary).EqualTo(whrVal2))
                            .And(Expression.Property(whrKey3).From(main).EqualTo(whrVal3))))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryLeftJoin([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["select_property"].ToString();
                int limit = (int)postBody["limit"];
                String main = "airline";
                String secondary = "route";

                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(
                           SelectResult.All().From(main),
                           SelectResult.All().From(secondary))
                       .From(DataSource.Database(db).As(main))
                       .Join(Join.LeftJoin(DataSource.Database(db).As(secondary))
                             .On(Meta.ID.From(main).EqualTo(Expression.Property(prop).From(secondary))))
                       .Limit(Expression.Int(limit)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryLeftOuterJoin([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                var prop = postBody["select_property"].ToString();
                int limit = (int)postBody["limit"];
                String main = "main";
                String secondary = "secondary";

                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                        .Select(
                           SelectResult.All().From(main),
                           SelectResult.All().From(secondary))
                       .From(DataSource.Database(db).As(main))
                       .Join(Join.LeftOuterJoin(DataSource.Database(db).As(secondary))
                             .On(Meta.ID.From(main).EqualTo(Expression.Property(prop).From(secondary))))
                       .Limit(Expression.Int(limit)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryArthimetic([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {

            List<Object> resultArray = new List<Object>();

            using (IQuery query = QueryBuilder
                            .Select(SelectResult.Expression(Meta.ID))
                            .From(DataSource.Database(db))
                            .Where(Expression.Property("number1").Modulo(Expression.Int(2))
                                    .EqualTo(Expression.Int(0))))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });

        }

        internal static void QueryInnerJoin([NotNull] NameValueCollection args,
           [NotNull] IReadOnlyDictionary<string, object> postBody,
           [NotNull] HttpListenerResponse response)
        {
            // SELECT
            //  employeeDS.firstname,
            //  employeeDS.lastname,
            //  departmentDS.name
            //FROM
            //  `travel-sample` employeeDS
            //  INNER JOIN `travel-sample` departmentDS ON employeeDS.department = departmentDS.code
            //WHERE
            //employeeDS.type = "employee"
            //AND departmentDS.type = "department"


            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var prop3 = postBody["select_property3"].ToString();
                var joinKey1 = postBody["join_key1"].ToString();
                var joinKey2 = postBody["join_key2"].ToString();
                var whrKey1 = postBody["whr_key1"].ToString();
                var whrKey2 = postBody["whr_key2"].ToString();
                var whrVal1 = postBody["whr_val1"].ToString();
                int whrVal2 = (int)postBody["whr_val2"];
                int limit = (int)postBody["limit"];
                String main = "route";
                String secondary = "airline";

                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                       .Select(
                           SelectResult.Expression(Expression.Property(prop1).From(main)),
                           SelectResult.Expression(Expression.Property(prop2).From(main)),
                           SelectResult.Expression(Expression.Property(prop3).From(secondary)))
                       .From(DataSource.Database(db).As(main))
                       .Join(Join.InnerJoin(DataSource.Database(db).As(secondary))
                             .On(Expression.Property(joinKey1).From(secondary).EqualTo(Expression.Property(joinKey2).From(main))
                                 .And(Expression.Property(whrKey1).From(secondary).EqualTo(Expression.String(whrVal1)))
                                 .And(Expression.Property(whrKey2).From(main).EqualTo(Expression.Int(whrVal2)))))
                       .Limit(Expression.Int(limit)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void QueryCrossJoin([NotNull] NameValueCollection args,
          [NotNull] IReadOnlyDictionary<string, object> postBody,
          [NotNull] HttpListenerResponse response)
        {
            //SELECT
            //  departmentDS.name AS DeptName,
            //  locationDS.name AS LocationName,
            //  locationDS.address
            //FROM
            //  `travel - sample` departmentDS
            //  CROSS JOIN `travel - sample` locationDS
            //WHERE
            //  departmentDS.type = "department"

            With<Database>(postBody, "database", db =>
            {
                var prop1 = postBody["select_property1"].ToString();
                var prop2 = postBody["select_property2"].ToString();
                var whrKey1 = postBody["whr_key1"].ToString();
                var whrKey2 = postBody["whr_key1"].ToString();
                var whrVal1 = postBody["whr_val1"].ToString();
                var whrVal2 = postBody["whr_val2"].ToString();
                int limit = (int)postBody["limit"];
                String main = "airport";
                String secondary = "airline";
                String firstName = "firstNamme";
                String secondName = "secondName";

                List<Object> resultArray = new List<Object>();

                using (IQuery query = QueryBuilder
                       .Select(
                           SelectResult.Expression(Expression.Property(prop1).From(main)).As(firstName),
                           SelectResult.Expression(Expression.Property(prop1).From(secondary)).As(secondName),
                           SelectResult.Expression(Expression.Property(prop2).From(secondary)))
                       .From(DataSource.Database(db).As(main))
                       .Join(Join.CrossJoin(DataSource.Database(db).As(secondary)))
                       .Where(Expression.Property(whrKey1).From(main).EqualTo(Expression.String(whrVal1))
                              .And(Expression.Property(whrKey2).From(secondary).EqualTo(Expression.String(whrVal2))))
                       .Limit(Expression.Int(limit)))

                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }
    }
}